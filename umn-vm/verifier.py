import base64
import socket
import os

from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
from impisc import logging
from impisc import packets


def main():
    original_phrase = os.getenv("IMPISH_PACKET_PASSPHRASE")
    passphrase = base64.urlsafe_b64encode(original_phrase.encode("utf-8")[:32])
    suite = Fernet(passphrase)

    port = int(os.getenv("RECV_PORT"))
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(("", port))
    while True:
        data, addr = receiver.recvfrom(2048)

        try:
            decrypted = suite.decrypt(data)
        except InvalidToken as e:
            logging.log_warning(f"Received invalid data from {addr}")
            continue

        try:
            header, packet = packets.split(data)
        except IndexError:
            logging.log_warning(f"Invalid header from {addr}")
            continue
        except ValueError:
            logging.log_warning(f"Invalid packet size from {addr}")
            continue

        # TODO
        ...


if __name__ == "__main__":
    main()
