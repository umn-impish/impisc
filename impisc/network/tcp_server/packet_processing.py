import ctypes
import socket


def forward_packet(bytes_):
    '''
    take the bytes which have been unframed from TCP
    and forward them to the appropriate process (as a UDP packet)
    '''
    # assume port is in little endian
    payload, port = unpack_payload(bytes_)

    # forward data to the payload
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(payload, ('localhost', port))


def pack_payload(payload: bytes, port: int) -> bytes:
    '''
    Pack the destination port onto the front
    of packet payload
    '''
    port = ctypes.c_uint16(port)
    return bytes(port) + payload


def unpack_payload(bytes_: bytes) -> tuple[bytes, int]:
    ''' Get port and payload from a packed set of bytes '''
    port = bytes_[0] | (bytes_[1] << 8)
    payload = bytes_[2:]
    return payload, port

