"""
Classes and such which support the ground system
"""

import copy
from ctypes import LittleEndianStructure, sizeof
from dataclasses import dataclass
import socket
import queue

from impisc.network.grips_given import TelemetryHeader, CommandAcknowledgement
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
        head = TelemetryHeader.from_buffer_copy(packet)
        type_ = packets.all_telemetry_packets.index(head.telem_type)

        # Forward acks to their own spot(s)
        if type_ == CommandAcknowledgement:
            endpoints = self.command_endpoints
        else:
            endpoints = self.telemetry_endpoints

        for ep in endpoints:
            self.resender.sendto(packet, ep)


class DecodedCommandAck:
    """Decode a command "ack" packet into something a little prettier"""

    def __init__(self, packet: CommandAcknowledgement):
        self.good = packet.error_type == packet.NO_ERROR
        self.issue = packet.HUMAN_READABLE_FAILURES[packet.error_type]
        self.command_number = packet.counter
        self.data = packet.error_data
        self.type = packets.all_commands[packet.cmd_type]


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
        packet = CommandAcknowledgement.from_buffer_copy(self.stream.recv(32768))
        self.queue.put(DecodedCommandAck(packet))


@dataclass
class LinuxCommandResponse:
    exit_code: int
    stdout: str
    stderr: str


@dataclass
class PacketPair:
    header: TelemetryHeader
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

    If data arrives out of order or only partially,
    stray packet bytes are pushed onto a "miscellaneous" queue
    which can be accessed separately.
    """

    def __init__(self, listen_socket: socket.socket, assumed_done_timeout: float):
        # The ready queue contains complete responses
        self.ready_queue: queue.Queue[LinuxCommandResponse] = queue.Queue()
        # The miscellaneous queue contains either stray data or out-of-order responses
        self.miscellaneous: queue.Queue[bytes] = queue.Queue()

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
        current_data = sort_telemetry_packets(current_data)

        response, misc = self._parse_response(current_data)
        if misc:
            self.miscellaneous.put(misc)

        self.ready_queue.put(response)

    def _receive_packet(self) -> PacketPair:
        # the receive chunk size is 128B, so 256B should fit the response
        # easily
        dat = self.socket.recv(256)
        head = TelemetryHeader.from_buffer_copy(dat)
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
        # Separate out any miscellaneous data
        data, misc = self._extract_misc(data)

        # Assemble the packets into the "string" response that we want,
        # and then parse it out
        reply = str()
        for d in data:
            pkt: packets.ArbitraryLinuxCommandResponse = d.payload
            resp: bytes = pkt.response
            reply += resp.decode("utf-8")
        # The reply may contain extraneous terminating null characters,
        # but for display that's fine

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
                        cmd_data[location] += chunk
            except KeyError as e:
                raise ValueError("Command reply is malformed") from e

        ret = LinuxCommandResponse(
            exit_code=int(cmd_data["exit_code"]),
            stdout=cmd_data["stdout"],
            stderr=cmd_data["stderr"],
        )
        return (ret, misc)

    def _extract_misc(self, data: list[PacketPair]) -> tuple[list[PacketPair], bytes]:
        misc = b""
        i = 0
        while i < len(data):
            cur_resp: packets.ArbitraryLinuxCommandResponse = data[i].payload
            start_of_message = cur_resp.response.startswith(
                b"ack-ok"
            ) or cur_resp.response.startswith(b"error")
            if not start_of_message:
                misc += bytes(data.pop(i).payload)
            i += 1
        return (data, misc)


def sort_telemetry_packets(packets: list[PacketPair]) -> list[PacketPair]:
    """Sort telemetry packets according to the "counter" supplied by the GRIPS headers,
    taking into account that there may be (at most) one wrap-around in packet number."""
    packets = copy.deepcopy(packets)

    # assume that we won't have more than 512 packets in a clump
    threshold = int(2**16 - 1 - 512)
    ordering = [h.counter for (h, _) in packets]

    # first, check if there is a wrap around
    wrapped = list()
    i = 0
    for i, x in enumerate(ordering):
        if abs(x - ordering[0]) > threshold:
            wrapped.append(i)

    # the wrapped packet counters need to get sorted separately
    separate = [packets.pop(i) for i in wrapped]
    packets.sort(key=lambda t: t[0].counter)
    separate.sort(key=lambda t: t[0].counter)

    return packets + separate
