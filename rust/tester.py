import socket

dest = ("localhost", 1234)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("localhost", 1235))
sock.setblocking(False)

while True:
    data = bytes(0xFF for _ in range(8005))
    sock.sendto(data, dest)
    try:
        dat = sock.recv(32768)
        assert len(dat) == 16005
        print(dat)
    except BlockingIOError:
        pass
