import json
import time
import socket

fc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

command = {
    "version": 1,
    "cmd": "set_mode",
    "mode": "science"
}

msg_bytes = json.dumps(command).encode('utf-8')
daq_box_addr = ("192.168.0.2", 8080)
fc_sock.sendto(msg_bytes, daq_box_addr)
time.sleep(0.2)

# fc_sock.settimeout(2.0)
# ack, _ = fc_sock.recfrom(1024)