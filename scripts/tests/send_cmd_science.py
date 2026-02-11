import json
import time
import ports
import socket

fc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

command = {
    "version": 1,
    "cmd": "set_mode",
    "mode": "science",
    "data_save": True
}

msg_bytes = json.dumps(command).encode('utf-8')
receiver = ("localhost", ports.science_udp_port)
fc_sock.sendto(msg_bytes, receiver)
time.sleep(0.2)

fc_sock.settimeout(10.0)
try:
    ack, _ = fc_sock.recvfrom(1024)
    print("ACK:", ack.decode())
except socket.timeout:
    print("No ACK received")