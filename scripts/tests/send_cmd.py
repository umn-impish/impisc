import json
import socket

# for debug

fc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

command = {
    "version": 1,
    "cmd": "set_mode",
    "mode": "debug",
    "params": {
        "n_waveforms": 3000,
        "n_spectra": 320
    }
}

msg_bytes = json.dumps(command).encode('utf-8')
receiver = ("192.168.0.2", 8080)
fc_sock.sendto(msg_bytes, receiver)

# fc_sock.settimeout(2.0)
# ack, _ = fc_sock.recfrom(1024)