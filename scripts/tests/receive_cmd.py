import json
import socket
import logging

IP = "192.168.0.3" # or "0.0.0.0" to listen on all interfaces?

def setup_command_socket(port=8080):
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
        logging.info(f'Received command: {cmd_data}')
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