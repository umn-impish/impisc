"""
Send random data to the relay.
This is used purely for testing.
"""


import argparse
import lzma
import random
import socket
import time


def main():
    """Endlessly loop and send data to the relay."""
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("send_port", type=int, help="the port to send the data from")
    _ = parser.add_argument("relay_addr", type=str, help="the relay address (xxx.xxx.xxx.xxx:port)")
    arg = parser.parse_args()
    MY_ADDR = ("", arg.send_port)
    a = arg.relay_addr.split(":")
    RELAY_ADDR = (a[0], int(a[1]))
    print(f"send address {MY_ADDR[0]}:{MY_ADDR[1]}")
    print(f"relay address {RELAY_ADDR[0]}:{RELAY_ADDR[1]}")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as send_sock:
        send_sock.bind(MY_ADDR)
        while True:
            data: bytes= random.randbytes(random.randint(16, 2048))
            print(len(data))
            compressed: bytes = lzma.compress(data, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64)
            print(f"sending {len(compressed)} bytes to {RELAY_ADDR[0]}:{RELAY_ADDR[1]}")
            print(f"compressed down from {len(data)} -> {len(compressed)} ({len(compressed) / len(data) * 100:0.1f})%")
            _ = send_sock.sendto(compressed, RELAY_ADDR)
            time.sleep(0.5)

    
if __name__ == "__main__":
    main()
