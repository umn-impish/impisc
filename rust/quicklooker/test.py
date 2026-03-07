import socket
import time

send = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
data = bytes(11 for r in range(8005))

recv.bind(("", 11111))
recipient = (("127.0.0.1", 12345))

while True:
    for _ in range(32):
        send.sendto(data, recipient)
        time.sleep(1/200)

    print(recv.recv(1000))
