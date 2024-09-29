from . import comm
from . import grips_given as gg
from . import packets
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
    route = comm.CommandRouter(remote_router_port)

    def dummy_callback(in_: comm.CommandInfo) -> gg.CommandAcknowledgement:
        # Construct a dummy packet with some data
        tel = packets.Dummy()
        data_size = len(tel.data)
        tel.data[:data_size] = [(i % 256) for i in range(data_size)]

        # Send dummy data over to the Telemeter
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(('0.0.0.0', remote_dummy_port))
        s.sendto(bytes(tel), ('localhost', in_.header.telemeter_port))

        # Say all went well
        return gg.CommandAcknowledgement()

    # Give dummy callback to the Router for later use
    route.add_callback(packets.Dummy, dummy_callback)

    # Set up the Telemeter to wrap and send data to our receive socket
    telemeter = comm.Telemeter(('localhost', local_data_port), remote_telem_port)
    telemeter.port_map[remote_dummy_port] = packets.Dummy

    print(cmd.send_recv_command_packet(
        packets.DummyCmd(), ('localhost', remote_router_port)
    ))
    # send GRIPS data via the telemeter
    telemeter.telemeter()
    
    # receive the GRIPS-wrapped data
    recvd = data_sock.recvfrom(1024)
    print(recvd)
