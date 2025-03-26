"""
Accept a stream of data from GRIPS and distribute it as needed
to other programs on the ground.
"""

import socket
import support
import ground_ports


def discriminate_packets():
    telemetry_endpoints: list[tuple[str, int]] = [
        ("localhost", ground_ports.TELEMETRY_SORTER),
        ("localhost", ground_ports.TELEMETRY_DUMP),
    ]

    command_ack_endpoints: list[tuple[str, int]] = [
        ("localhost", ground_ports.COMMAND_ACK_DISPLAY),
        ("localhost", ground_ports.COMMAND_ACK_DUMP),
    ]

    main_stream = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    main_stream.bind(("", ground_ports.MAIN_DATA_PIPE))

    splitter = support.PacketDiscriminator(
        resend_port=ground_ports.DISCRIMINATOR,
        data_stream=main_stream,
        telemetry_endpoints=telemetry_endpoints,
        command_endpoints=command_ack_endpoints,
    )

    while True:
        splitter.route()


if __name__ == "__main__":
    discriminate_packets()
