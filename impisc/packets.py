import ctypes
import time

from typing import TypeAlias


class HealthPacket(ctypes.LittleEndianStructure):
    """
    The IMPISH health packet

    Contains health information on temperatures, voltages,
    and other quantities from different parts of the system.

    Once this is developed to something we're happy with,
    we should make a GitHub release.
    """

    # Reserved bytes for additional data
    EXTRA_BYTES = 64

    # Do not include padding bytes
    _pack_ = 1

    # Update fields
    _fields_ = [
        # Voltages on the power lines; measured in centivolts
        ("cm4_volts", ctypes.c_uint8),
        # heater volts
        ("heater_volts", ctypes.c_uint8),
        # DAQBOX volts
        ("daqbox_volts", ctypes.c_uint8),
        # +- SiPM preamp input voltages
        ("sipm_preamp_pos_volts", ctypes.c_uint8),
        ("sipm_preamp_neg_volts", ctypes.c_uint8),
        # +- bubba input voltages
        ("bubba_input_pos_volts", ctypes.c_uint8),
        ("bubba_input_neg_volts", ctypes.c_uint8),
        # bubba output bias voltage (~30V to ~50V)
        ("bubba_output_volts", ctypes.c_uint16),
        ("bubba_wiper", ctypes.c_uint8),
        # Power toggle status byte
        ("power_line_statuses", ctypes.c_uint8),
        # Disk usages in 10 MiB units
        ("os_disk_usage", ctypes.c_uint16),
        ("data_disk_usage", ctypes.c_uint16),
        # Temperatures from RTDs; measured in Celsius to integer precision
        # Rename once we assign them locations within the payload
        ("temperature_rtd1", ctypes.c_int8),
        ("temperature_rtd2", ctypes.c_int8),
        ("temperature_rtd3", ctypes.c_int8),
        ("temperature_rtd4", ctypes.c_int8),
        ("temperature_rtd5", ctypes.c_int8),
        ("temperature_rtd6", ctypes.c_int8),
        ("temperature_rtd7", ctypes.c_int8),
        ("temperature_rtd8", ctypes.c_int8),
        ("temperature_rtd9", ctypes.c_int8),
        # In units of centikelvin
        ("cpu_temperature", ctypes.c_uint16),
        ("cpu0_usage", ctypes.c_uint16),
        ("cpu1_usage", ctypes.c_uint16),
        ("cpu2_usage", ctypes.c_uint16),
        ("cpu3_usage", ctypes.c_uint16),
        ("ram_usage", ctypes.c_uint16),
        ("swap_usage", ctypes.c_uint16),
        ("timestamp", ctypes.c_uint32),
        # Padding on the end of the health packet:
        # remove bytes from this as needed
        # to add packet fields after flight starts.
        ("extra", EXTRA_BYTES * ctypes.c_uint8),
        # Missing fields: one bit per field missing, in order
        ("missing_fields", ctypes.c_uint16),
    ]


class PacketHeader(ctypes.LittleEndianStructure):
    """A packet header has four fields:
    - an identifier number (id) specifying packet type
    - a packet number, total packet counter
    - a sequence number, sequenced per packet type
    - packet size in bytes, as a sanity check
    """

    _pack_ = 1
    _fields_ = (
        ("id", ctypes.c_uint8),
        ("packet_number", ctypes.c_uint16),
        ("sequence_number", ctypes.c_uint16),
        ("packet_size", ctypes.c_uint16),  # EXCLUDING header size
    )


HEADER_SIZE = ctypes.sizeof(PacketHeader)
MAX_SEQUENCE_NUMBER = int(2**16) - 1  # packet header uses uint16


# A command response packet is just a blob of bytes.
# They can be used however deemed fit.
class CommandResponsePacket(ctypes.LittleEndianStructure):
    DELIMITER = b"\x1d"  # group separator
    NUM_RESP_CHARS: int = 512
    PAYLOAD_FIELDS: list[str] = ["status_code", "cmd", "stdout", "stderr"]
    _pack_ = 1
    _fields_ = (
        ("payload", ctypes.c_uint8 * NUM_RESP_CHARS),
        ("timestamp", ctypes.c_uint32),
        ("command_counter", ctypes.c_uint8),
        ("response_sequence", ctypes.c_uint16),
        ("total_packets_in_response", ctypes.c_uint16),
    )

    @classmethod
    def from_parts(cls, ret_code: int, command: str, stdout: str, stderr: str):
        """Build a packet given the payload parts."""
        packet = cls()
        packet.timestamp = int(time.time())
        packet.command_counter = 0xFF  # max number; can't put a "real" one
        packet.response_sequence = 0
        packet.total_packets_in_response = 1
        code = bytes(ctypes.c_uint8(ret_code))
        message = cls.DELIMITER.join(
            part.encode("utf-8") for part in (command, stdout, stderr)
        )
        message = code + cls.DELIMITER + message
        lim = min(cls.NUM_RESP_CHARS, len(message))
        packet.payload[:lim] = message[:lim]

        return packet


NUM_QUICKLOOK_BINS = 4
NUM_DET_CHANNELS = 4


class QuicklookPacket(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = (
        ("timestamp", ctypes.c_uint32),
        ("daqbox_frame_counter", ctypes.c_uint8),
        # 2D array: each channel gets a number of quicklook bins
        ("channels", NUM_DET_CHANNELS * (NUM_QUICKLOOK_BINS * ctypes.c_uint32)),
    )


Packet: TypeAlias = (
    type[HealthPacket] | type[QuicklookPacket] | type[CommandResponsePacket]
)
# Define a unique ID for each packet type; their index in their ID value
PACKET_IDS: list[Packet] = [HealthPacket, QuicklookPacket, CommandResponsePacket]


def split(data: bytes) -> tuple[PacketHeader, Packet]:
    """Split a full packet's bytes into a header and payload."""
    header = PacketHeader.from_buffer_copy(data[:HEADER_SIZE])
    PacketClass: Packet = PACKET_IDS[header.id]
    packet = PacketClass.from_buffer_copy(data[HEADER_SIZE:])

    return header, packet
