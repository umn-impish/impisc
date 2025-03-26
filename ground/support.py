"""
Classes and such which support the ground system
"""

import copy
from ctypes import LittleEndianStructure, sizeof
from dataclasses import dataclass
import socket
import queue

from impisc.network import packets


class PacketDiscriminator:
    """
    Accepts a bound socket which will be the main data pipe from GRIPS.
    Splits up data into different streams depending on the telemetry type.

    The user supplies destinations as (address, socket number) pairs to forward data to.
    The IP addresses are expected to be bound UDP sockets,
    otherwise the data will be lost in the void.
    """

    def __init__(
        self,
        resend_port: int,
        data_stream: socket.socket,
        telemetry_endpoints: list[tuple[str, int]],
        command_endpoints: list[tuple[str, int]],
    ):
        self.stream = data_stream
        self.resender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.resender.bind(("localhost", resend_port))

        self.telemetry_endpoints = telemetry_endpoints
        self.command_endpoints = command_endpoints

    def route(self):
        packet, _ = self.stream.recvfrom(int(2**16))
        head = packets.TelemetryHeader.from_buffer_copy(packet)
        type_ = packets.all_telemetry_packets[head.telem_type]

        # Forward acks to their own spot(s)
        if type_ == packets.CommandAcknowledgement:
            endpoints = self.command_endpoints
        else:
            endpoints = self.telemetry_endpoints

        for ep in endpoints:
            self.resender.sendto(packet, ep)


class DecodedCommandAck:
    """Decode a command "ack" packet into something a little prettier"""

    def __init__(self, packet: packets.CommandAcknowledgement):
        self.good = packet.error_type == packet.NO_ERROR
        self.issue = packet.HUMAN_READABLE_FAILURES[packet.error_type]
        self.command_number = packet.counter
        self.data = packet.error_data
        self.type = packets.all_commands[packet.cmd_type]

    def __repr__(self):
        bookend = "-" * 30
        return "\n".join(
            [
                bookend,
                f"Execution {'succeeded' if self.good else 'failed'}",
                f"Issue (if present): {self.issue}",
                f"Command sequence number: {self.command_number}",
                f"Error data: {list(self.data)}",
                f"Error data (raw): {bytes(self.data)}",
                f"Command type: {self.type.__qualname__}",
                bookend,
            ]
        )


class CommandAckQueue:
    """
    A queue that receives packets and holds onto acks.
    The acks get formatted as objects instead of raw GRIPS packets,
    which makes them easier to touch elsewhere in the program.
    """

    def __init__(
        self,
        data_stream: socket.socket,
        history_length: int = 10,
    ):
        self.stream = data_stream
        self.queue = queue.Queue(maxsize=history_length)

    def accept_new(self):
        """Await data to arrive on the stream and push command acknowledgements onto the queue."""
        packet = packets.CommandAcknowledgement.from_buffer_copy(
            self.stream.recv(32768)
        )
        self.queue.put(DecodedCommandAck(packet))


@dataclass
class LinuxCommandResponse:
    exit_code: int
    stdout: str
    stderr: str

    def __repr__(self):
        bookend = "-" * 30
        exit_msg = f"Exit code: {self.exit_code}"
        stdout_msg = f"stdout:\n{self.stdout}"
        stderr_msg = f"stderr:\n{self.stderr}"
        return "\n".join([bookend, exit_msg, stdout_msg, stderr_msg, bookend])


@dataclass
class PacketPair:
    header: packets.TelemetryHeader
    payload: LittleEndianStructure


class LinuxCommandResponseParser:
    """
    Accepts a stream of packets from the "arbitrary linux command"
    output and parses them into a coherent response.

    The assumption is that after a given timeout (seconds),
    the response packets will stop being transmitted for a given command.

    The resulting command information is parsed into chunks:
        - exit code
        - stdout
        - stderr
    and pushed onto a queue. The queue may be read elsewhere.
    """

    def __init__(self, listen_socket: socket.socket, assumed_done_timeout: float):
        # The ready queue contains complete responses
        self.ready_queue: queue.Queue[LinuxCommandResponse] = queue.Queue()

        self.socket = listen_socket
        self.timeout = assumed_done_timeout
        # Start socket in blocking mode
        self.socket.settimeout(None)

    def accept_and_enqueue(self):
        try:
            current_data = [self._receive_packet()]
            #
            self.socket.settimeout(self.timeout)
            while True:
                current_data.append(self._receive_packet())
        except socket.timeout:
            # we're done getting data,
            # so restore the infinite timeout
            self.socket.settimeout(None)

        # Sequence numbers sent by the cmd executor
        # are independent and per-session compared to the spacecraft
        # packets
        unadultured_seq_nums = [d.payload.seq_num for d in current_data]
        current_data = sort_telemetry_packets(
            current_data, ordering=unadultured_seq_nums
        )
        response = self._parse_response(current_data)

        self.ready_queue.put(response)

    def _receive_packet(self) -> PacketPair:
        # the receive chunk size is 128B, so 256B should fit the response
        # easily
        dat = self.socket.recv(256)
        head = packets.TelemetryHeader.from_buffer_copy(dat)
        packet = packets.ArbitraryLinuxCommandResponse.from_buffer_copy(
            dat, sizeof(head)
        )
        return PacketPair(head, packet)

    def _parse_response(
        self, data: list[PacketPair]
    ) -> tuple[LinuxCommandResponse, bytes]:
        """
        Accept a sorted list of packet pairs (which potentially has stray data),
        and return a parsed version of the data.
        If the stray data is present, it is returned along with the parsed portion.
        """
        data = copy.deepcopy(data)

        # Assemble the packets into the "string" response that we want,
        # and then parse it out
        reply = str()
        for d in data:
            pkt: packets.ArbitraryLinuxCommandResponse = d.payload
            resp = bytes(pkt.response)
            reply += resp.decode("utf-8")

        # Now, split the data up by newlines and chunk it up
        split = reply.split("\n")
        cmd_data = {"exit_code": "", "stdout": "", "stderr": ""}
        location = None
        for chunk in split:
            try:
                match chunk:
                    case "ack-ok":
                        location = "exit_code"
                    case "error":
                        location = "exit_code"
                    case "arb-cmd-stdout":
                        location = "stdout"
                    case "arb-cmd-stderr":
                        location = "stderr"
                    case _:
                        cmd_data[location] += chunk + "\n"
            except KeyError as e:
                raise ValueError("Command reply is malformed") from e

        ret = LinuxCommandResponse(
            exit_code=int(cmd_data["exit_code"]),
            stdout=cmd_data["stdout"],
            stderr=cmd_data["stderr"],
        )
        return ret  # (ret, misc)


def sort_telemetry_packets(
    packets: list[PacketPair], ordering: list[int] = None
) -> list[PacketPair]:
    """Sort telemetry packets according to the "counter" supplied by the GRIPS headers,
    taking into account that there may be (at most) one wrap-around in packet number."""
    packets = copy.deepcopy(packets)

    # assume that we won't have more than 512 packets in a clump
    threshold = int(2**16 - 1 - 512)
    ordering = ordering or [h.header.counter for h in packets]

    # first, check if there is a wrap around
    wrapped = list()
    i = 0
    for i, x in enumerate(ordering):
        if abs(x - ordering[0]) > threshold:
            wrapped.append(i)

    # the wrapped packet counters need to get sorted separately
    separate = [packets.pop(i) for i in wrapped]
    packets.sort(key=lambda t: t.header.counter)
    separate.sort(key=lambda t: t.header.counter)

    return packets + separate
