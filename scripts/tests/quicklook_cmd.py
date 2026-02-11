import time
import json
import ports
import socket

addr = ("127.0.0.1", ports.quicklook_port)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_quicklook(adc_ranges, counts_per_range, count_rate_per_sec, num_seconds:int):
    msg = {
        "type": "quicklook",
        "t_send": time.time(),
        "num_seconds": num_seconds,
        "adc_ranges": adc_ranges,
        "counts_per_range": counts_per_range,
        "count_rate_per_sec": count_rate_per_sec,
    }
    sock.sendto(json.dumps(msg).encode(), addr)