import json
import socket
import logging

# Receiver/listening functions -- random IPs and ports

IP = "0.0.0.0"

def setup_command_socket(port=5000):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((IP, port))
    sock.setblocking(False)
    return sock


def update_flight_mode(sock):
    try:
        data, addr = sock.recvfrom(1024)
    except BlockingIOError:
        return None, None
        
    try:
        cmd_data = json.loads(data.decode('utf-8'))
        logging.info(f'Received command {cmd_data} mode')
        return cmd_data, addr

    except Exception as e:
        logging.warning(f'Bad command packet: {e}')
        return None, None

def send_ack(sock, addr, cmd, status, current_mode, error=None):
    ack = {
        "ack": True,
        "cmd": cmd.get("cmd"),
        "status": status,
        "current_mode": current_mode.name
    }

    if error:
        ack["error"] = error
    
    sock.sendto(json.dumps(ack).encode('utf-8'), addr)