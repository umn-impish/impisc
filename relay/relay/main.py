"""
Constantly listen for data sent by IMPISH.
This is meant to mock the gondola computer.
"""


import argparse
import socket
import syslog
import time

from collections import deque
from pathlib import Path
from struct import pack
from threading import Thread
from typing import Never, override


LOG_DIR = Path("")
BUFFER_MAX_LENGTH = int(1e5)


class Buffer(deque[bytes]):
    """deque object with syslogging."""
    def __init__(self, maxlen: int | None = None) -> None:
        super().__init__(maxlen=maxlen)
    
    @override
    def append(self, x: bytes, /) -> None:
        """Append with logging."""
        if len(self) == self.maxlen:
            syslog.syslog(
                syslog.LOG_DEBUG,
                f"buffer at capacity; dropping one item"
            )
        super().append(x)
        syslog.syslog(
            syslog.LOG_DEBUG,
            f"appended to buffer; new size: {len(self)}"
        )


def connect_to_impish() -> socket.socket:
    """Establish a socket for communication with IMPISH."""
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def connect_to_groundstation() -> socket.socket:
    """Establish a socket for communication with the ground station."""
    return socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def receive_from_impish(buf: Buffer, recv_port: int) -> None:
    """Receive data from IMPISH."""
    data: bytes
    addr: tuple[str, int]
    while True:
        with connect_to_impish() as recv_sock:
            recv_sock.bind(("", recv_port))
            data, addr = recv_sock.recvfrom(65000)
            buf.append(data)
            syslog.syslog(
                syslog.LOG_DEBUG,
                f"Received {len(data):>9} bytes from {addr[0]}:{addr[1]}"
            )


def send_to_groundstation(buf: Buffer, fwd_addr: tuple[str, int]) -> None:
    """Dump the full buffer into the ground station."""
    addr_str = f"{fwd_addr[0]}:{fwd_addr[1]}"
    while buf:
        with connect_to_groundstation() as send_sock:
            try:
                send_sock.connect(fwd_addr)
            except ConnectionRefusedError as e:
                syslog.syslog(
                    syslog.LOG_WARNING,
                    f"Connection to ground station ({addr_str}) refused: {e}"
                )
                break
            data: bytes = buf.popleft()
            length: bytes = pack(">Q", len(data))
            syslog.syslog(
                syslog.LOG_DEBUG,
                f"Sending {len(data):>10} bytes to ground station ({addr_str})"
            )
            send_sock.sendall(length)
            send_sock.sendall(data)


def main() -> Never:
    """Endlessly loop and listen for data from IMPISH and
    forward to the ground station.
    """
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("port", type=int, help="the port to bind the relay to")
    _ = parser.add_argument("fwd_addr", type=str, help="the address to forward to (xxx.xxx.xxx.xxx:port)")
    arg = parser.parse_args()
    RELAY_PORT = arg.port
    a = arg.fwd_addr.split(":")
    FWD_ADDR = (a[0], int(a[1]))
    print(f"Relay port: {RELAY_PORT}")
    buffer: Buffer = Buffer(maxlen=BUFFER_MAX_LENGTH)
    recv_thread: Thread = Thread(
        target=receive_from_impish,
        args=[buffer, RELAY_PORT],
        daemon=True
    )
    recv_thread.start()
    while True:
        send_to_groundstation(buffer, FWD_ADDR)
        time.sleep(5)

    
if __name__ == "__main__":
    main()
