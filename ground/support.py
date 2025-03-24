'''
Classes and such which support the ground system
'''
import socket
import queue

from impisc.network import grips_given
from impisc.network import packets


class PacketDiscriminator:
    '''
    Accepts a bound socket which will be the main data pipe from GRIPS.
    Splits up data into different streams depending on the telemetry type.

    The user supplies destinations as (address, socket number) pairs to forward data to.
    The IP addresses are expected to be bound UDP sockets,
    otherwise the data will be lost in the void. 
    '''
    def __init__(
        self,
        resend_port: int,
        data_stream: socket.socket,
        telemetry_endpoints: list[tuple[str, int]],
        command_endpoints: list[tuple[str, int]],
    ):
        self.stream = data_stream
        self.resender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.resender.bind(('localhost', resend_port))

        self.telemetry_endpoints = telemetry_endpoints
        self.command_endpoints = command_endpoints

    def route(self):
        packet, _ = self.stream.recvfrom(int(2**16))
        head = grips_given.TelemetryHeader.from_buffer_copy(packet)
        type_ = packets.all_telemetry_packets.index(head.telem_type)

        # Forward acks to their own spot(s)
        if type_ == grips_given.CommandAcknowledgement:
            endpoints = self.command_endpoints
        else:
            endpoints = self.telemetry_endpoints

        for ep in endpoints:
            self.resender.sendto(packet, ep)


class DecodedCommandAck:
    '''Decode a command "ack" packet into something a little prettier'''
    def __init__(self, packet: grips_given.CommandAcknowledgement):
        self.good = (packet.error_type == packet.NO_ERROR)
        self.issue = packet.HUMAN_READABLE_FAILURES[
            packet.error_type
        ]
        self.command_number = packet.counter
        self.data = packet.error_data
        self.type = packets.all_commands[packet.cmd_type]


class CommandAckQueue:
    '''
    A queue that receives packets and holds onto acks.
    The acks get formatted as objects instead of raw GRIPS packets,
    which makes them easier to touch elsewhere in the program.
    '''
    def __init__(
        self,
        data_stream: socket.socket,
        history_length: int=10,
    ):
        self.stream = data_stream
        self.queue = queue.Queue(maxsize=history_length)

    def accept_new(self):
        packet = grips_given.CommandAcknowledgement.from_buffer_copy(
            self.stream.recv(32768)
        )
        self.queue.put(DecodedCommandAck(packet))
