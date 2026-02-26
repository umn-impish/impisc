import os
import time
import json
import ports
import socket
import logging

# my_port = int(os.getenv("QUICKLOOK_MONITOR_PORT"))
my_port = ports.quicklook_port
addr = ("127.0.0.1", my_port)

def send_quicklook(packet):
    msg = {
        "type": "quicklook",
        "unix_timestamp": time.time(),
        "det_ebin1": packet["det_ebin1"], # upper bound of the bins
        "det_ebin2": packet["det_ebin2"],
        "det_ebin3": packet["det_ebin3"],
        "det_ebin4": packet["det_ebin4"],
        "det1_ebin1_counts": packet["det1_ebin1_counts"],
        "det1_ebin2_counts": packet["det1_ebin2_counts"],
        "det1_ebin3_counts": packet["det1_ebin3_counts"],
        "det1_ebin4_counts": packet["det1_ebin4_counts"],

        "det2_ebin1_counts": packet["det2_ebin1_counts"],
        "det2_ebin2_counts": packet["det2_ebin2_counts"],
        "det2_ebin3_counts": packet["det2_ebin3_counts"],
        "det2_ebin4_counts": packet["det2_ebin4_counts"],

        "det3_ebin1_counts": packet["det3_ebin1_counts"],
        "det3_ebin2_counts": packet["det3_ebin2_counts"],
        "det3_ebin3_counts": packet["det3_ebin3_counts"],
        "det3_ebin4_counts": packet["det3_ebin4_counts"],

        "det4_ebin1_counts": packet["det4_ebin1_counts"],
        "det4_ebin2_counts": packet["det4_ebin2_counts"],
        "det4_ebin3_counts": packet["det4_ebin3_counts"],
        "det4_ebin4_counts": packet["det4_ebin4_counts"],

        "det1_ebin1_cps": packet["det1_ebin1_cps"],
        "det2_ebin2_cps": packet["det2_ebin2_cps"],
        "det3_ebin3_cps": packet["det3_ebin3_cps"],
        "det4_ebin4_cps": packet["det4_ebin4_cps"],
    }
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(json.dumps(msg).encode(), addr)
    except Exception as e:
        logging.warning(f"Quicklook UDP send failed: {e}")