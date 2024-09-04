'''
Assumes the command_executor script is running in the background
'''

import subprocess

lines = subprocess.run(['ps', 'aux'], stdout=subprocess.PIPE).stdout.decode('utf-8').split()
if not any(('command_executor' in l) for l in lines):
    raise RuntimeError("Command executor process has to be running")

import impisc.network.comm as com
import impisc.network.ports as por
import impisc.network.grips_given as gg
from impisc.network import packets as pkt

import ctypes
import socket

def test_router_executor():
    cmd = b'echo "hello, bingus"'
    cmd_pkt = pkt.ArbitraryLinuxCommand()
    cmd_pkt.command[:len(cmd)] = cmd

    router_addr = ('localhost', por.GRIPS_LISTENER)
    my_address = ('localhost', 54321)

    me = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    me.bind(my_address)
    me.settimeout(2)

    com.send_command_packet(
        cmd_pkt,
        router_addr,
        given_socket=me
    )

    ack = gg.CommandAcknowledgement.from_buffer_copy(me.recv(2048))

    while True:
        try:
            bytes_back = bytearray(me.recv(2048))
        except socket.timeout:
            break
        sz = ctypes.sizeof(gg.TelemetryHeader)
        payload = pkt.ArbitraryLinuxCommandResponse.from_buffer(bytes_back[sz:])
        print(bytes(payload.response).decode('utf-8'))

    if ack.error_type != 0:
        raise RuntimeError("Didn't get a good packet reply.")
