from . import comm
from . import grips_given as gg
from . import packets
import ctypes
import socket

def test_cmd_telemetry_loop():
    '''
    Define a dummy "telemetry loop" to test the functionality
    of command routing, acknowledgement, and telemetering 
    independent of the actual implementation of IMPISH stuff.
    '''
    local_cmd_port = 12345
    local_data_port = 12346
    remote_router_port = 12347
    remote_telem_port = 12348
    remote_dummy_port = 12349

    data_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    data_sock.bind(('0.0.0.0', local_data_port))

    cmd = comm.Commander(local_cmd_port)
    # The command router needs to know where to
    # listen for packets, as well as where to route the
    # ensuing telemetry data
    route = comm.CommandRouter(remote_router_port, remote_telem_port)

    def dummy_callback(in_: comm.CommandInfo) -> gg.CommandAcknowledgement:
        # Construct a dummy packet with some data
        tel = packets.Dummy()
        data_size = len(tel.data)
        tel.data[:data_size] = [(i % 256) for i in range(data_size)]

        # Send dummy data over to the Telemeter
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(('0.0.0.0', remote_dummy_port))
        print(in_.header.telemeter_port)
        s.sendto(bytes(tel), ('localhost', in_.header.telemeter_port))

        # Say all went well
        return gg.CommandAcknowledgement()

    # Set up the Telemeter to wrap and send data to our receive socket
    telemeter = comm.Telemeter(('localhost', local_data_port), remote_telem_port)
    telemeter.port_map[remote_dummy_port] = packets.Dummy

    # Send command
    cmd.send_command(
        packets.DummyCmd(), ('localhost', remote_router_port)
    )

    # Route it to the right spot
    # Give dummy callback to the Router to use
    route.add_callback(packets.DummyCmd, dummy_callback)
    route.listen_and_route()

    # send GRIPS data via the telemeter
    # this should also send the command Ack back to the Commander
    telemeter.telemeter()

    # print out the command reply
    print(cmd.recv_ack())
    
    # receive the GRIPS-wrapped data
    recvd = data_sock.recv(1024)
    # TODO decode telemetry packets
    head = gg.TelemetryHeader.from_buffer_copy(recvd)
    data = packets.Dummy.from_buffer_copy(recvd, ctypes.sizeof(head))
    print(head.gondola_time)
    print(list(data.data))
