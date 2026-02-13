"""
This receives the data from the relay.
This is intended to be deployed on the ground station.
"""


import argparse
import lzma
import socket

from struct import unpack

# GROUND_STATION_ADDR = ("10.131.217.250", 15001)


def main():
    """Endlessly loop, receiving data from the relay."""
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("port", type=int, help="the port to bind to for receiving data")
    arg = parser.parse_args()
    RECV_PORT = arg.port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as recv_sock:
        recv_sock.bind(("", RECV_PORT))
        recv_sock.listen(1)
        while True:
            connection, addr = recv_sock.accept()
            buff = connection.recv(8)
            (length,) = unpack(">Q", buff)
            data = b""
            while len(data) < length:
                to_read = length - len(data)
                data += connection.recv(4096 if to_read > 4096 else to_read)
            assert length == len(data)
            print(f"received {len(data)} bytes from {addr[0]}:{addr[1]}")
            uncompressed = lzma.decompress(data, format=lzma.FORMAT_XZ)
            print(f"uncompressed -> {len(uncompressed)}")


if __name__ == "__main__":
    main()
