from impisc.network import comm
from impisc.network import packets
from impisc.network import ports


def telemeter():
    telem = comm.Telemeter((ports.GRIPS_IP, ports.GRIPS_EXPOSED), ports.TELEMETER)

    # Update these as more things get added
    telem.port_map[ports.ARBITRARY_LINUX_COMMAND_TELEM] = (
        packets.ArbitraryLinuxCommandResponse
    )
    telem.port_map[ports.COMMAND_ROUTER] = packets.CommandAcknowledgement

    while True:
        telem.telemeter()


if __name__ == "__main__":
    telemeter()
