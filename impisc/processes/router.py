'''
Process to accept commands from GRIPS and
route them to appropriate processes on the flight computer.

Based on the command ID, the packet is routed
to the appropriate process.

The process may reply with data straightaway,
or it may save it to disk and send an acknowledge or error
indicator.

The behavior is defined by the respective process
and the corresponding function in this file.
'''
import socket
from impisc.network import ports
from impisc.network import comm
from impisc.network import grips_given as gg
from impisc.network import packets

def route_data(sock: socket.socket):
    '''
    Receive data from GRIPS as well as other processes,
    and route it to the appropriate place.
    '''
    try:
        cmd, sender = comm.receive_grips_packet(sock)
        print(cmd)
    except gg.AcknowledgeError as e:
        # ruh roh!
        bad = gg.CommandAcknowledgement.from_err(e)
        sender = e.source 
        comm.send_formatted_packet(
            bad,
            sender,
        )
        return

    # Map each command to its process with a bunch of 'if' statements
    if type(cmd) == packets.ArbitraryLinuxCommand:
        sock.sendto(
            cmd.command, ('localhost', ports.COMMAND_EXECUTOR)
        )
        arb_command_handler(sock, sender)


def arb_command_handler(
        sock: socket.socket,
        sender: tuple[str, int],
):
    replies = []
    orig_timeout = sock.gettimeout()
    sock.settimeout(60)
    while True:
        try: dat = sock.recv(2048)
        except socket.timeout: break

        if dat == b'finished':
            break

        replies.append(
            packets.ArbitraryLinuxCommandResponse
                    .from_buffer_copy(dat)
        )
    sock.settimeout(orig_timeout)

    # sort the packets out to be in correct order
    replies.sort(key=lambda r: r.seq_num)
    ack_pkt = gg.CommandAcknowledgement()
    bad = (len(replies) == 0) or (
        bytes(replies[0].response).startswith(b'error')
    )
    if bad:
        ack_pkt.error_type = gg.CommandAcknowledgement.GENERAL_FAILURE
    comm.send_formatted_packet(bytes(ack_pkt), sender)
    for r in replies:
        comm.send_telemetry_packet(r, sender, r.seq_num)


def main():
    listen = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen.bind(('', ports.GRIPS_LISTENER))
    listen.settimeout(None)

    while True:
        route_data(listen)


if __name__ == '__main__':
    main()

