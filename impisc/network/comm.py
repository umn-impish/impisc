'''
Module for properly sending and receiving GRIPS
packets (telemetry and commands).

The packets are defined in `impish_packets.py`.
As more packets are added, the packet IDs get updated
as the lists `all_commands` and `all_telemetry_packets` grow.

These functions are meant to be imported in the command
distributor process(es) and data downlink process(es).
'''
import ctypes
import socket

from impisc.network import grips_given as gg
import impisc.network.packets as imppa

# Commands that IMPISH defines
# Map from ID to type
# ID is determined by ordering in all_commands
COMMAND_MAP = {
    i: c
    for (i, c) in enumerate(imppa.all_commands)
}
# Telemetry we define
# Map from type to ID
# ID is determined by ordering in all_telemetry_packets
TELEMETRY_MAP = {
    c: i
    for (i, c) in enumerate(imppa.all_telemetry_packets)
}

def send_telemetry_packet(
    pkt,
    address: tuple[str, int],
    given_socket: socket.socket | None=None,
    counter: int=0
):
    '''
    Send a properly-formatted GRIPS packet from an
    unwrapped IMPISH packet.
    '''
    # Build the header from metadata
    head = gg.TelemetryHeader()
    head.telem_type = TELEMETRY_MAP[type(pkt)]
    head.counter = counter

    # Attach the GRIPS header
    full_packet = bytes(head) + bytes(pkt)
    send_formatted_packet(full_packet, address, given_socket)


def send_command_packet(
    pkt,
    address: tuple[str, int],
    given_socket: socket.socket | None=None,
    counter: int=0,
):
    head = gg.CommandHeader()
    head.cmd_type = imppa.all_commands.index(type(pkt))
    head.counter = counter
    head.size = ctypes.sizeof(pkt)
    send_formatted_packet(bytes(head) + bytes(pkt), address, given_socket)


def send_formatted_packet(
    full_packet: bytes,
    address: tuple[str, int],
    given_socket: socket.socket | None=None
):
    # Put in the CRC and verify it worked
    ba = bytearray(full_packet)
    gg.apply_crc16(ba)
    gg.verify_crc16(ba)

    # Send data off via a random socket
    # or a provided one
    s = given_socket or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(ba, address)


def receive_grips_packet(sock: socket.socket) -> tuple[ctypes.LittleEndianStructure, tuple[str, int]]:
    '''
    Receive a GRIPS packet assuming its command header structure.

    Goes through all of the  steps to verify
    the packet is good as per the error codes defined
    in the network specification.

    If all looks well, then the packet is decoded from the given type
    and sent onwards.
    Else, an error is thrown.

    Returns tuple of:
        - decoded struct
        - sender address
    '''
    # bigger buffer than we will ever need
    BUFSZ = 32768
    data, addr = sock.recvfrom(BUFSZ)
    return decode_grips_packet(data, addr)


def decode_grips_packet(data: bytes, addr: tuple[str, int]) -> tuple[ctypes.LittleEndianStructure, tuple[str, int]]:
    '''
    Same as `receive_grips_packet` but expects
    the data to be presented as bytes already.
    '''
    data = bytearray(data)

    head_sz = ctypes.sizeof(gg.CommandHeader)
    if len(data) < head_sz:
        raise gg.AcknowledgeError(
            gg.CommandAcknowledgement.PARTIAL_HEADER,
            data,
            addr
        )

    decoded = gg.CommandHeader.from_buffer(data)

    if decoded.base_header.sync != gg.GRIPS_SYNC:
        raise gg.AcknowledgeError(
            gg.CommandAcknowledgement.INVALID_SYNC,
            data[:2],
            addr
        )

    try:
        gg.verify_crc16(data)
    except gg.CrcError as e:
        raise gg.AcknowledgeError(
            gg.CommandAcknowledgement.INCORRECT_CRC,
            bytes(e.received) + bytes(e.computed),
            addr
        )

    if decoded.base_header.system_id != gg.IMPISH_SYSTEM_ID:
        raise gg.AcknowledgeError(
            gg.CommandAcknowledgement.INCORRECT_SYSTEM_ID,
            bytes(decoded.system_id),
            addr
        )

    if decoded.cmd_type not in COMMAND_MAP:
        raise gg.AcknowledgeError(
            gg.CommandAcknowledgement.INVALID_COMMAND_TYPE,
            bytes(decoded.cmd_type),
            addr
        )

    actual_packet_length = ctypes.c_uint8(len(data) - head_sz).value
    reported_length = decoded.size
    if actual_packet_length != reported_length:
        raise gg.AcknowledgeError(
            gg.CommandAcknowledgement.INCORRECT_PACKET_LENGTH,
            bytes(actual_packet_length) + bytes(reported_length),
            addr
        )

    # Now we have verified a lot of details;
    # we can pick the correct command type confidently
    cmd_type = COMMAND_MAP[decoded.cmd_type]
    if decoded.size != ctypes.sizeof(cmd_type):
        raise gg.AcknowledgeError(
            gg.CommandAcknowledgement.INVALID_PACKET_LENGTH,
            bytes(decoded.size),
            addr
        )

    # Invalid parameters, busy, and other
    # errors must be handled separately.
    return (
        cmd_type.from_buffer(data[head_sz:]),
        addr
    )
