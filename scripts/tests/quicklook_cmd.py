import os
import time
import json
import ports
import socket

my_port = int(os.getenv("QUICKLOOK_MONITOR_PORT"))
# my_port = ports.quicklook_port
addr = ("127.0.0.1", my_port)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_quicklook_ch1(
        det1_ebin1, det1_ebin2, det1_ebin3, det1_ebin4,
        det1_ebin1_counts, det1_ebin2_counts, det1_ebin3_counts, det1_ebin4_counts,
        det1_ebin1_cps, det1_ebin2_cps, det1_ebin3_cps, det1_ebin4_cps
        ):
    msg = {
        "type": "quicklook",
        "unix_timestamp": time.time(),
        "det1_ebin1": det1_ebin1,
        "det1_ebin2": det1_ebin2,
        "det1_ebin3": det1_ebin3,
        "det1_ebin4": det1_ebin4,
        "det1_ebin1_counts": det1_ebin1_counts,
        "det1_ebin2_counts": det1_ebin2_counts,
        "det1_ebin3_counts": det1_ebin3_counts,
        "det1_ebin4_counts": det1_ebin4_counts,
        "det1_ebin1_cps": det1_ebin1_cps,
        "det1_ebin2_cps": det1_ebin2_cps,
        "det1_ebin3_cps": det1_ebin3_cps,
        "det1_ebin4_cps": det1_ebin4_cps,
    }
    sock.sendto(json.dumps(msg).encode(), addr)