import json
import socket

# also random IPs and ports for now

fc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

command = {
    "version": 1,
    "cmd": "set_mode",
    "mode": "science",
    "params": {
        "n_waveforms": 3000,
        "n_spectra": 320
    }
}

msg_bytes = json.dumps(command).encode('utf-8')
receiver = ("127.0.0.1", 5000)
fc_sock.sendto(msg_bytes, receiver)