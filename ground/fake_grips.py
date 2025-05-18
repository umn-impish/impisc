"""
Accept packets and forward them elsewhere.
"""

from impisc.network import ports
import ground_ports
import socket


def fake_grips():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((ports.GRIPS_IP, ports.GRIPS_EXPOSED))
    destination = (ground_ports.TELEM_SORTER_IP, ground_ports.MAIN_DATA_PIPE)

    while True:
        data = s.recv(32768)
        s.sendto(data, destination)


if __name__ == "__main__":
    fake_grips()
