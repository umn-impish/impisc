"""
Module for properly sending and receiving GRIPS
packets (telemetry and commands).

The packets are defined in `impish_packets.py`.
As more packets are added, the packet IDs get updated
as the lists `all_commands` and `all_telemetry_packets` grow.

These functions are meant to be imported in the command
distributor process(es) and data downlink process(es).
"""

# TODO add decoder functionality for telemetry packets
import ctypes
import socket
import time
from typing import Callable

from . import grips_given as gg
from . import packets as imppa

# Commands that IMPISH defines
# Map from ID to type
# ID is determined by ordering in all_commands
COMMAND_MAP = {i: c for (i, c) in enumerate(imppa.all_commands)}
# Telemetry we define
# Map from type to ID
# ID is determined by ordering in all_telemetry_packets
TELEMETRY_MAP = {c: i for (i, c) in enumerate(imppa.all_telemetry_packets)}


def send_telemetry_packet(
    pkt,
    address: tuple[str, int],
    counter: int,
    given_socket: socket.socket | None = None,
):
    """
    Send a telemetry packet wrapped in the GRIPS format
    from a 'native' IMPISH packet.
    """
    # Build the header from metadata
    head = gg.TelemetryHeader()
    head.telem_type = TELEMETRY_MAP[type(pkt)]
    head.counter = counter

    # Attach the GRIPS header
    full_packet = bytes(head) + bytes(pkt)
    send_grips_telem_bytes(full_packet, address, given_socket)


def send_grips_telem_bytes(
    full_packet: bytes,
    address: tuple[str, int],
    given_socket: socket.socket | None = None,
):
    # Put current system time into "GondolaTime"
    # before sending out the data
    ba = bytearray(full_packet)
    th = gg.TelemetryHeader.from_buffer(ba)
    th.gondola_time = int(time.time())

    send_grips_bytes(bytes(ba), address, given_socket)


def send_grips_bytes(
    pkt: bytes, address: tuple[str, int], given_socket: socket.socket | None
):
    # Put in the CRC and verify it worked
    ba = bytearray(pkt)
    gg.apply_crc16(ba)
    gg.verify_crc16(ba)

    # Send data off via a random socket
    # or a provided one
    s = given_socket or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(ba, address)


def receive_command(
    sock: socket.socket,
) -> tuple[ctypes.LittleEndianStructure, tuple[str, int]]:
    """
    Receive a GRIPS packet assuming its command header structure.
    """
    # bigger buffer than we will ever need
    BUFSZ = 32768
    data, addr = sock.recvfrom(BUFSZ)
    return decode_command(data, addr)


def decode_command(data: bytes, addr: tuple[str, int]) -> dict:
    """
    Goes through all of the  steps to verify that
    the packet is good as per the error codes defined
    in the GRIPS network specification.

    If all looks well, then the packet is decoded from the given type
    and returned.
    Else, an error is thrown.

    Returns dict of:
        - packet header
        - decoded packet contents
        - sender address
    """
    data = bytearray(data)

    head_sz = ctypes.sizeof(gg.CommandHeader)
    if len(data) < head_sz:
        raise gg.AcknowledgeError(
            gg.CommandAcknowledgement.PARTIAL_HEADER, data, addr, 255, imppa.UnknownCmd
        )

    decoded = gg.CommandHeader.from_buffer(data)

    if decoded.base_header.sync != gg.GRIPS_SYNC:
        raise gg.AcknowledgeError(
            gg.CommandAcknowledgement.INVALID_SYNC,
            data[:2],
            addr,
            decoded.counter,
            imppa.UnknownCmd,
        )

    try:
        gg.verify_crc16(data)
    except gg.CrcError as e:
        raise gg.AcknowledgeError(
            error_type=gg.CommandAcknowledgement.INCORRECT_CRC,
            error_data=bytes(e.received) + bytes(e.computed),
            cmd_source_addr=addr,
            cmd_seq_num=decoded.counter,
            cmd_type=imppa.UnknownCmd,
        )

    if decoded.base_header.system_id != gg.IMPISH_SYSTEM_ID:
        raise gg.AcknowledgeError(
            gg.CommandAcknowledgement.INCORRECT_SYSTEM_ID,
            bytes(decoded.system_id),
            addr,
            decoded.counter,
            imppa.UnknownCmd,
        )

    if decoded.cmd_type not in COMMAND_MAP:
        raise gg.AcknowledgeError(
            gg.CommandAcknowledgement.INVALID_COMMAND_TYPE,
            bytes(decoded.cmd_type),
            addr,
            decoded.counter,
            imppa.UnknownCmd,
        )

    # Now we have verified a lot of details;
    # we can pick the correct command type confidently
    cmd_type = COMMAND_MAP[decoded.cmd_type]

    actual_packet_length = ctypes.c_uint8(len(data) - head_sz).value
    reported_length = decoded.size
    if actual_packet_length != reported_length:
        raise gg.AcknowledgeError(
            gg.CommandAcknowledgement.INCORRECT_PACKET_LENGTH,
            bytes(actual_packet_length) + bytes(reported_length),
            addr,
            decoded.counter,
            cmd_type,
        )

    if decoded.size != ctypes.sizeof(cmd_type):
        raise gg.AcknowledgeError(
            gg.CommandAcknowledgement.INVALID_PACKET_LENGTH,
            bytes(decoded.size),
            addr,
            decoded.counter,
            cmd_type,
        )

    # Invalid parameters, busy, and other
    # errors must be handled separately.
    return {
        "header": decoded,
        "contents": cmd_type.from_buffer(data, head_sz),
        "sender": addr,
    }


def grips_cmd_header_from_packet(pkt: ctypes.LittleEndianStructure, seq_num: int):
    """
    Construct a command header given a "known" packet type.
    Just a wrapper around the constructor, but incorporates
    the information within `impish.network.packets.all_commands` to
    assign the cmd_type.
    """
    head = gg.CommandHeader()
    head.cmd_type = imppa.all_commands.index(type(pkt))
    head.counter = seq_num
    head.size = ctypes.sizeof(pkt)
    return head


class CommandInfo:
    """Information on a command:
    - sender addr
    - cmd seq. num
    - command payload
    """

    def __init__(self):
        self.sender: tuple[str, int] = ("", 0)
        self.seq_num: int = 0
        self.payload: ctypes.LittleEndianStructure = None


class Commander:
    """Use this to send commands to the IMPISH payload on GRIPS.
    Tracks the "sequence number" as part of the object state.

    The sequence number is supposed to be a monotonically-increasing
    integer up to its maximum (255). This is used on-board
    to track if commands are coming in properly or if they are
    arriving out of order.

    The user must deal with out-of-sync sequence numbers.
    """

    def __init__(self, port: int):
        self.sequence_number = 0
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("0.0.0.0", port))

    def send_command(
        self,
        pkt: ctypes.LittleEndianStructure,
        address: tuple[str, int],
    ) -> None:
        """Send a packet wrapped in the GRIPS command header
        to the given address, via the given socket.
        Useful on the ground and for testing.
        Returns the cmd response.
        """
        try:
            head = grips_cmd_header_from_packet(pkt, self.sequence_number)
        except KeyError:
            raise ValueError(f"{type(pkt)} is an unrecognized command")

        # Might throw; wait to increment seq_num until after call
        send_grips_bytes(bytes(head) + bytes(pkt), address, self.socket)
        # Sequence number can only be in [0, 255]
        # because it's a u8
        self.sequence_number += 1
        self.sequence_number %= 256

    def recv_ack(self) -> gg.CommandAcknowledgement:
        # The command acknoqledgement should arrive synchronously
        # right after sending the command.
        res_dat = self.socket.recv(2048)
        return gg.CommandAcknowledgement.from_buffer_copy(res_dat)


# May raise an AcknowledgeError if something goes wrong.
RouterCallback = Callable[[CommandInfo], gg.CommandAcknowledgement]


class CommandRouter:
    """
    Listens for incoming command packets.
    They get decoded by helper functions (defined above),
    and then mapped to callbacks which the user provides.

    In this way, commands may be validated and decoded
    via the standard GRIPS 'telemetry stream',
    but testing is a hell of a lot easier because
    the callbacks can be customized per-test.

    There should only be one instance of the CommandRouter
    active on the spacecraft.
    """

    def __init__(self, listen_port: int, reply_to: None):
        self.cmd_map = dict()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("0.0.0.0", listen_port))

        # Keep track of the command sequence number as part
        # of the object state
        self.expected_cmd_seq_num = None

        # If we want to "hard-code" where
        # we need to send the replies back to
        self.reply_to = reply_to

    def add_callback(self, command: type, callback: RouterCallback) -> None:
        self.cmd_map[command] = callback

    def listen_and_route(self) -> None:
        """Wait for a command on the bound socket and
        pass the data to the proper callback.

        Throws an error if the callback isn't present,
        or if there is an issue during command execution.
        The issue is properly reported back to the sender;
        no need to do that on your own <3
        """

        # Parse a received command into structured data
        ci = CommandInfo()
        try:
            recvd_cmd = receive_command(self.socket)
            ci.payload = recvd_cmd["contents"]
            ci.sender = recvd_cmd["sender"]
            ci.seq_num = recvd_cmd["header"].counter
        except gg.AcknowledgeError as e:
            # We had a problem verifying the cmd packet
            # structure
            self._handle_error(e)

        try:
            self._track_seq_num(ci)
        except gg.AcknowledgeError as e:
            # The sequence number was out of order
            self._handle_error(e)

        # Fetch the appropriate callback for the given command
        try:
            cback = self.cmd_map[type(ci.payload)]
        except KeyError as e:
            raise ValueError(
                f"The type {type(ci.payload)} is not present in the registered callbacks."
            ) from e

        # Get the ack from the callback and send it back to the command
        try:
            ack = cback(ci)
        except gg.AcknowledgeError as e:
            # There was an error during
            # command execution
            self._handle_error(e)

        # If we clear all the try/except blocks:
        #     send off a "good" ack packet
        self.socket.sendto(bytes(ack), (self.reply_to or ci.sender))

    def _track_seq_num(self, ci: CommandInfo) -> None:
        """Keep track of the command packet sequence number
        relative to what we expect.
        If it fails, throw an AckError.
        """
        # Set upon receipt of first command
        if self.expected_cmd_seq_num is None:
            self.expected_cmd_seq_num = ci.seq_num

        if self.expected_cmd_seq_num != ci.seq_num:
            raise gg.AcknowledgeError(
                error_type=gg.CommandAcknowledgement.GENERAL_FAILURE,
                error_data=list(b"badsqn") + [self.expected_cmd_seq_num],
                cmd_source_addr=ci.sender,
                cmd_seq_num=ci.seq_num,
                cmd_type=type(ci.payload),
            )

        # Increment the number in expectation of the next command
        self.expected_cmd_seq_num += 1
        self.expected_cmd_seq_num %= 256

    def _handle_error(self, e: gg.AcknowledgeError) -> None:
        """If we get an error from some portion of the
        command process, parse it to an Ack packet
        and send it off.
        """
        bad = gg.CommandAcknowledgement.from_err(e)
        sender = e.cmd_source_addr
        send_grips_telem_bytes(bad, sender, given_socket=self.socket)
        raise UserWarning("Packet error occurred during parsing/verification")


class Telemeter:
    """
    Handles telemetry packets as they come in from foreign
    sources over a UDP socket.

    Meaning, packets get decoded, wrapped, and then
    sent back out to a different destination, wherever that may be.

    There should only be one instance of a Telemeter running
    on the payload so that the sequence number is properly
    ... well, sequenced.
    """

    def __init__(self, dest_addr: tuple[str, int], listen_port: int):
        self.destination = dest_addr
        self.sequence_number: int = 0
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("0.0.0.0", listen_port))

        # The port map provides a way for mapping replies from
        # various processes to different types.
        # Making it an argument in the constructor would be
        # another way to do this, but this achieves the
        # same result and makes the ad-hoc intention clearer--
        # you have to update things after object initialization.
        self.port_map: dict[int, type[ctypes.LittleEndianStructure]] = dict()

    def telemeter(self) -> None:
        """
        Wait on the object's UDP socket until some data comes in;
        it is assumed that the data is a telemetry packet from
        a recognized source.

        The packet-sender's port is used to decode the proper
        type of the packet, and the decoded packet is
        sent to the stored destination address.

        The telemetry sequence number is maintained in the
        interval [0, 2^16).
        """
        data, (_, port) = self.socket.recvfrom(65535)
        type_ = self.port_map[port]
        send_telemetry_packet(
            type_.from_buffer_copy(data),
            self.destination,
            self.sequence_number,
            self.socket,
        )

        self.sequence_number += 1
        self.sequence_number %= int(2**16)
