"""
Define some helper functions for the relay.
We're currently just using TCP to forward packets
to the ground station because it's the simplest thing
to do until we get further details from StarSpec.
We use Python's deque object because it
is thread safe.
"""

import socket
import syslog

from collections import deque
from pathlib import Path
from struct import pack
from typing import override


class Buffer(deque[bytes]):
    """deque object with syslogging."""

    def __init__(self, maxlen: int | None = None) -> None:
        super().__init__(maxlen=maxlen)

    @override
    def append(self, x: bytes, /) -> None:
        """Append with logging."""
        if len(self) == self.maxlen:
            syslog.syslog(syslog.LOG_DEBUG, f"buffer at capacity; dropping one item")
        super().append(x)
        syslog.syslog(syslog.LOG_DEBUG, f"appended to buffer; new size: {len(self)}")


def impish_socket() -> socket.socket:
    """Establish a UDP socket for communication with IMPISH."""
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def connect_tcp(addr: tuple[str, int]) -> socket.socket:
    """Establish a TCP socket for communication with the specified address."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(addr)
    except ConnectionRefusedError as e:
        syslog.syslog(
            syslog.LOG_WARNING, f"Connection to {addr[0]}:{addr[1]} refused: {e}"
        )
    return sock


def receive_from_impish(buf: Buffer, recv_port: int) -> None:
    """Receive data from IMPISH and append it to the provided buffer.
    This function infinitely loops, waiting for data from IMPISH.
    It is intended to be ran in a separate thread.
    """
    data: bytes
    addr: tuple[str, int]
    with impish_socket() as recv_sock:
        recv_sock.bind(("", recv_port))
        while True:
            data, addr = recv_sock.recvfrom(1024)
            buf.append(data)
            syslog.syslog(
                syslog.LOG_DEBUG,
                f"Received {len(data):>9} bytes from {addr[0]}:{addr[1]}",
            )


def tcp_forward_to(buf: Buffer, fwd_addr: tuple[str, int]) -> None:
    """Dump the full buffer into the forwarding address.
    Sends the data as TCP packets.
    """
    while buf:
        try:
            with connect_tcp(fwd_addr) as send_sock:
                data: bytes = buf.popleft()
                length: bytes = pack(">Q", len(data))
                syslog.syslog(
                    syslog.LOG_DEBUG,
                    f"Sending {len(data):>10} bytes to {fwd_addr[0]}:{fwd_addr[1]}",
                )
                send_sock.sendall(length)
                send_sock.sendall(data)
        except ConnectionRefusedError:
            break
