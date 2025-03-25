"""
Process to accept commands from GRIPS and
route them to appropriate processes on the flight computer.

Based on the command ID, the packet is routed
to the appropriate process.

The process may reply with data straightaway,
or it may save it to disk and send an acknowledge or error
indicator.

The behavior is defined by the respective process
and the corresponding function in this file.
"""

import socket
import sys
from impisc.network import ports
from impisc.network import comm
from impisc.network import grips_given as gg
from impisc.network import packets


def log_packet_error(e: UserWarning):
    # For now just . . . print it
    print("packet error:", e, file=sys.stderr)


def route_data():
    """
    Receive data from GRIPS as well as other processes,
    and route it to the appropriate place.
    """
    router = comm.CommandRouter(ports.COMMAND_ROUTER)

    # Add callbacks here as they become relevant
    router.add_callback(packets.ArbitraryLinuxCommand, arb_command_handler)

    while True:
        try:
            router.listen_and_route()
        except UserWarning as e:
            log_packet_error(e)


def arb_command_handler(ci: comm.CommandInfo) -> gg.CommandAcknowledgement:
    # Send the command over to the
    # appropriate process from the desired port
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", ports.ARBITRARY_LINUX_COMMAND_TELEM))

    # Assume correct type already assigned
    sock.sendto(ci.payload.cmd)

    # Await the telemetry replies
    replies: list[packets.ArbitraryLinuxCommandResponse] = []
    orig_timeout = sock.gettimeout()
    # Give the Linux command an execution time limit (s)
    sock.settimeout(60)
    while True:
        try:
            dat = sock.recv(2048)
        except socket.timeout:
            break

        if dat == b"arb-cmd-finished":
            break

        replies.append(packets.ArbitraryLinuxCommandResponse.from_buffer_copy(dat))
    sock.settimeout(orig_timeout)

    # sort the packets out to be in correct order
    replies.sort(key=lambda r: r.seq_num)
    # Send packets out to the Telemeter process
    for r in replies:
        # Drop the packet-local seq num
        sock.sendto(bytes(r.response), ("localhost", ports.TELEMETER))

    # After forwarding telemetry,
    # return an appropriate ack to the cmd sender
    # (either OK or an error)
    bad = (len(replies) == 0) or (bytes(replies[0].response).startswith(b"error"))
    if bad:
        raise gg.AcknowledgeError(
            gg.CommandAcknowledgement.GENERAL_FAILURE,
            "cmderr",
            ci.sender,
            ci.seq_num,
            cmd_type=type(ci.payload),
        )

    # Everything went ok
    ack = gg.CommandAcknowledgement()
    ack.pre_send(ci.seq_num, packets.all_commands.index(type(ci.payload)))
    return ack


if __name__ == "__main__":
    route_data()
