"""
Accept telemetry packets on a port and route them elsewhere depending on the
type of the packet.
"""

# Configure the logging if you want
import logging

logging.basicConfig(level=logging.INFO)

import ground_ports
import socket
from impisc.network import packets
from umndet.common import impress_exact_structs as ies


def sort_telemetry():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("", ground_ports.TELEMETRY_SORTER))

    telemetry_map = {
        packets.ArbitraryLinuxCommandResponse: ground_ports.COMMAND_INTERFACE,
        ies.DetectorHealth: ground_ports.DETECTOR_HEALTH_DUMP,
    }

    while True:
        data = s.recv(8192)
        # Immediately dump data to the big telemetry file (redundancy)
        s.sendto(data, ("localhost", ground_ports.TELEMETRY_DUMP))

        # Get the type from the header; forward if applicable
        head = packets.TelemetryHeader.from_buffer_copy(data)
        try:
            type_ = packets.all_telemetry_packets[head.telem_type]
            dest = telemetry_map[type_]
            s.sendto(data, ("localhost", dest))
        except KeyError:
            logging.warning(
                f"Telemetry type not in the forwarding map: [{head.telem_type:d} | {repr(type_)}]"
            )


if __name__ == "__main__":
    sort_telemetry()
