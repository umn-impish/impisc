from . import comm
from . import grips_given as gg
from . import packets
import ctypes
import pytest
import socket


def test_cmd_telemetry_loop():
    """
    Define a dummy "telemetry loop" to test the functionality
    of command routing, acknowledgement, and telemetering
    independent of the actual implementation of IMPISH stuff.

    This does not explore any "exceptional" conditions;
    those are tested separately.
    """
    local_cmd_port = 12345
    local_data_port = 12346
    remote_router_port = 12347
    remote_telem_port = 12348
    remote_dummy_port = 12349

    data_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data_sock.bind(("0.0.0.0", local_data_port))

    cmd = comm.Commander(local_cmd_port)
    # The command router needs to know where to
    # listen for packets
    route = comm.CommandRouter(remote_router_port)

    def dummy_callback(in_: comm.CommandInfo) -> gg.CommandAcknowledgement:
        # Construct a dummy packet with some data
        tel = packets.Dummy()
        data_size = len(tel.data)
        tel.data[:data_size] = [(i % 256) for i in range(data_size)]

        # Send dummy data over to the Telemeter
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("0.0.0.0", remote_dummy_port))
        # Assume the port is known via either an envar or
        # some other import
        s.sendto(bytes(tel), ("localhost", remote_telem_port))

        # Say all went well
        return gg.CommandAcknowledgement()

    # Set up the Telemeter to wrap and send data to our receive socket
    telemeter = comm.Telemeter(("localhost", local_data_port), remote_telem_port)
    telemeter.port_map[remote_dummy_port] = packets.Dummy

    # Send command
    cmd.send_command(packets.DummyCmd(), ("localhost", remote_router_port))

    # Route it to the right spot
    # Give dummy callback to the Router to use
    route.add_callback(packets.DummyCmd, dummy_callback)
    route.listen_and_route()

    # send GRIPS data via the telemeter
    # this should also send the command Ack back to the Commander
    telemeter.telemeter()

    # Shouldn't throw
    cmd.recv_ack()

    # receive the GRIPS-wrapped data
    recvd = data_sock.recv(1024)
    head = gg.TelemetryHeader.from_buffer_copy(recvd)
    data = packets.Dummy.from_buffer_copy(recvd, ctypes.sizeof(head))

    # Verify that the data is the same as we sent.
    assert all(
        [
            d == dd
            for (d, dd) in
            # The data we sent is just [0, 1, 2, ..., 255]
            zip(list(range(len(data.data))), data.data)
        ]
    )


def test_exceptional_router():
    """
    Test whether or not the command router
    can handle exceptions properly.
    Should manage these conditions:
        - Malformed command (AckError reply to cmd sender)
        - No callback present for cmd (throws ValueError)
        - Callback throws an AckError: reply to cmd sender

    As a side effect, the sequence number synchronization
    between the Commmander and CommandRouter are tested
    for the simple cases of (0, 1).
    """
    # Test the "bad command case"
    router = comm.CommandRouter(
        (route_port := 23451),
    )
    cmd_port = 23461
    good_cback = lambda *_: gg.CommandAcknowledgement()
    router.add_callback(packets.DummyCmd, good_cback)

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("", cmd_port))

    # Construct and send a malformed command
    # which has an uninitialized header (CRC is wrong, CMD ID is wrong)
    bad_dummy = packets.DummyCmd()
    empty_head = gg.CommandHeader()
    total = bytes(empty_head) + bytes(bad_dummy)
    s.sendto(total, route_addr := ("localhost", route_port))

    # After sending the bad command, test the logic
    # inside the `listen_and_route` method to ensure
    # it actually throws.
    # In flight we can log this to systemd journal
    with pytest.raises(UserWarning):
        router.listen_and_route()

    # Receive the ack packet; verify it; shouldn't throw
    ackd = gg.CommandAcknowledgement.from_buffer_copy(s.recv(1024))
    gg.verify_crc16(bytearray(ackd))

    assert ackd.HUMAN_READABLE_FAILURES[ackd.error_type] == "INCORRECT_CRC"

    # Now test the 'unrecognized command' case
    # The command needs to be real, though.
    del s
    # Replace with no callbacks
    router.cmd_map = {}
    cdr = comm.Commander(cmd_port)
    # Send a proper "DummyCmd" with header etc. formatted
    # in the correct way, but it isn't registered with the Router
    cdr.send_command(packets.DummyCmd(), route_addr)

    # The command does not have a registered callback;
    # should throw an error at this point as
    # the command verificiation has succeeded
    with pytest.raises(ValueError):
        router.listen_and_route()

    # See what happens when a callback throws an AckError
    def bad_cback(ci: comm.CommandInfo):
        raise gg.AcknowledgeError(
            gg.CommandAcknowledgement.BUSY,
            error_data=[],
            cmd_source_addr=ci.sender,
            cmd_seq_num=ci.seq_num,
            cmd_type=type(ci.payload),
        )

    router.add_callback(packets.DummyCmd, bad_cback)
    cdr.send_command(packets.DummyCmd(), route_addr)

    # The callback should raise and then send a reply
    # back to the commander
    with pytest.raises(UserWarning):
        router.listen_and_route()

    reply = cdr.recv_ack()
    assert reply.error_type == gg.CommandAcknowledgement.BUSY


def test_exceptional_commander():
    """Test if the Commander class can properly
    handle exception conditions, and that its
    sequence numbering properly ticks up over time.

    We expect a few possibliities:
      - A command is unrecognized (throws)
      - ...

    I guess that's the only exceptional condition
    that needs to get treated explicitly.
    A malformed command ack packet will definitely
    throw, but we don't need to do any special checks
    for that in the class definition itself.
    """
    cdr = comm.Commander(54321)

    class StupidType(ctypes.LittleEndianStructure):
        pass

    with pytest.raises(ValueError):
        cdr.send_command(StupidType(), ("localhost", 54322))

    del cdr
    cdr = comm.Commander(54321)
    # Receive the packets individually and just verify the
    # sequence numbers
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind(("", 0))
    recv_addr = receiver.getsockname()
    # Go for several "sequence number rollovers" to make sure
    # things keep working.
    for i in range(12345):
        cdr.send_command(packets.DummyCmd(), recv_addr)
        cmd_dat = receiver.recv(2048)
        head = gg.CommandHeader.from_buffer_copy(cmd_dat)
        assert head.counter == (i % 256)
