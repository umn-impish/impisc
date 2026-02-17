import os
import json
import ports
import socket

# for debug and maybe quicklook

my_port = int(os.getenv("SCIENCE_CMD_PORT"))
# my_port = ports.cmd_port
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

command = {
    "version": 1,
    "cmd": "set_mode",
    "mode": "debug",
    "data_save": True,
    "params": {
        "n_waveforms": 3000,
        "n_spectra": 320
    }
}

msg_bytes = json.dumps(command).encode('utf-8')
receiver = ("localhost", my_port)
sock.sendto(msg_bytes, receiver)
print(f"Sent command to {receiver}: {command}")

sock.settimeout(10.0)
try:
    ack, _ = sock.recvfrom(1024)
    print("ACK:", ack.decode())
except socket.timeout:
    print("No ACK received")