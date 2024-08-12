'''
Execute arbitrary Linux commands sent in over a UDP socket.

Packet input:
    - command to execute (1 KiB max length)

Reply packet(s):
    - command output split into 1KiB chunks,
      to be reassembled elsewhere
'''
import ctypes
import socket
import subprocess

from impisc.network import ports
from impisc.network import packets


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Port we listen on and maybe send on
    s.bind(('', ports.COMMAND_EXECUTOR))

    # never gonna hit this size (...)
    bufsz = 32768
    while True:
        data, requestor = s.recvfrom(bufsz)
        cmd_packet = packets.ArbitraryLinuxCommand.from_buffer_copy(data)

        try:
            cmd = bytes(cmd_packet.command)
            cmd = cmd[:cmd.index(0)].decode('utf-8')
        except ValueError:
            cmd = bytes(cmd_packet.command).decode('utf-8')
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True
        )
        reply_head = (b'ack-ok\n' if result.returncode == 0 else b'error\n')
        res_bytes = (
            reply_head + 
            b'retc:' + bytes(ctypes.c_uint8(result.returncode)) +
            b'\n' +
            b'stdout:' + result.stdout +
            b'\n' + 
            b'stderr:' + result.stderr
        )

        res_size = ctypes.sizeof(
            packets.CommandCharArray
        )
        reply_packets = []
        i = 0
        # chunk the data into 1KiB packets
        while i < len(res_bytes):
            reply_packet = packets.ArbitraryLinuxCommandResponse()
            end = i + res_size
            chunk = res_bytes[i:end]
            reply_packet.response[:len(chunk)] = chunk

            # Keep track of packet ordering so we can reconstruct the info
            reply_packet.seq_num = (i % res_size)
            reply_packets.append(reply_packet)
            i += res_size

        # Send response off to the requestor
        for rp in reply_packets:
            s.sendto(bytes(rp), requestor)


if __name__ == '__main__':
    main()