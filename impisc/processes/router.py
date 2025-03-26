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
import traceback
from impisc.network import ports
from impisc.network import comm
from impisc.network import packets


def log_packet_error(e: UserWarning):
    # For now just . . . print it
    print("packet error:", e, file=sys.stderr)
    traceback.print_exc()


def route_data():
    """
    Receive data from GRIPS as well as other processes,
    and route it to the appropriate place.
    """
    router = comm.CommandRouter(
        listen_port=ports.COMMAND_ROUTER,
        # Send all acks directly back to GRIPS
        reply_to=(ports.GRIPS_IP, ports.GRIPS_EXPOSED),
    )

    # Add callbacks here as they become relevant
    router.add_callback(packets.ArbitraryLinuxCommand, arb_command_handler)

    while True:
        try:
            router.listen_and_route()
        except UserWarning as e:
            log_packet_error(e)


def arb_command_handler(ci: comm.CommandInfo) -> packets.CommandAcknowledgement:
    # Send the command over to the
    # appropriate process from the desired port
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", ports.ARBITRARY_LINUX_COMMAND_TELEM))

    # Assume correct type already assigned
    payload: packets.ArbitraryLinuxCommand = ci.payload
    sock.sendto(payload.command, ("localhost", ports.COMMAND_EXECUTOR))

    # Await the telemetry replies
    replies: list[packets.ArbitraryLinuxCommandResponse] = []
    orig_timeout = sock.gettimeout()
    # Give the Linux command an execution time limit (s)
    COMMAND_TIMEOUT_SECONDS = 5
    sock.settimeout(COMMAND_TIMEOUT_SECONDS)
    while True:
        try:
            dat = sock.recv(2048)
        except socket.timeout:
            break

        if dat == b"arb-cmd-finished":
            break

        replies.append(packets.ArbitraryLinuxCommandResponse.from_buffer_copy(dat))
    sock.settimeout(orig_timeout)

    # Send packets out to the Telemeter process
    for r in replies:
        sock.sendto(r, ("localhost", ports.TELEMETER))

    # After forwarding telemetry,
    # return an appropriate ack to the cmd sender
    # (either OK or an error)
    process_dead = len(replies) == 0
    execution_error = (not process_dead) and (
        bytes(replies[0].response).startswith(b"error")
    )
    if process_dead or execution_error:
        message = "prdead" if process_dead else "excerr"
        err = packets.AcknowledgeError(
            error_type=packets.CommandAcknowledgement.GENERAL_FAILURE,
            error_data=message.encode("utf-8"),
            cmd_source_addr=ci.sender,
            cmd_seq_num=ci.seq_num,
            cmd_type=packets.ArbitraryLinuxCommand,
        )
        ack = packets.CommandAcknowledgement.from_err(err)
    else:
        ack = packets.CommandAcknowledgement()
        ack.pre_send(ci.seq_num, packets.all_commands.index(type(ci.payload)))

    return ack


if __name__ == "__main__":
    route_data()
