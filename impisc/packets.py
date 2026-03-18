import ctypes


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
        ("cm4_volts", ctypes.c_uint8),
        # +- SiPM preamp input voltages
        ("sipm_preamp_pos_volts", ctypes.c_uint8),
        ("sipm_preamp_neg_volts", ctypes.c_uint8),
        # should the heater turn on, track its voltage
        ("heater_volts", ctypes.c_uint8),
        # +- bubba input voltages
        ("bubba_input_pos_volts", ctypes.c_uint16),
        ("bubba_input_neg_volts", ctypes.c_uint16),
        # bubba output bias voltage (~30V to ~50V)
        ("bubba_output_volts", ctypes.c_uint16),
        ("bubba_wiper", ctypes.c_uint8),
        # Power toggle status byte
        ("power_line_statuses", ctypes.c_uint8),
        # Disk usages in 10 MiB units
        ("os_disk_usage", ctypes.c_uint16),
        ("data_disk_usage", ctypes.c_uint16),
        # In units of centikelvin
        ("cpu_temperature", ctypes.c_uint16),
        ("cpu0_usage", ctypes.c_uint16),
        ("cpu1_usage", ctypes.c_uint16),
        ("cpu2_usage", ctypes.c_uint16),
        ("cpu3_usage", ctypes.c_uint16),
        ("ram_usage", ctypes.c_uint16),
        ("swap_usage", ctypes.c_uint16),
        ("unix_timestamp", ctypes.c_uint32),
        # Padding on the end of the health packet:
        # remove bytes from this as needed
        # to add packet fields after flight starts.
        ("extra", EXTRA_BYTES * ctypes.c_uint8),
        # Missing fields: one bit per field missing, in order
        ("missing_fields", ctypes.c_uint16),
    ]


MAX_SEQUENCE_NUMBER = int(2**16) - 1  # packet header uses uint16
class PacketHeader(ctypes.LittleEndianStructure):
    """ A packet header has three fields:
        - an identifier number (id) specifying packet type
        - a sequence number
        - packet size in bytes, as a sanity check
    """

    _pack_ = 1
    _fields_ = (
        ("id", ctypes.c_uint8),
        ("sequence_number", ctypes.c_uint16),
        ("packet_size", ctypes.c_uint16),  # EXCLUDING header size
    )


# A command response packet is just a blob of bytes.
# They can be used however deemed fit.
class CommandResponsePacket(ctypes.LittleEndianStructure):
    NUM_RESP_CHARS = 512
    _pack_ = 1
    _fields_ = (
        ("response", ctypes.c_char * NUM_RESP_CHARS),
        ("sequence", ctypes.c_uint16),  # What is this?
    )

    def add_response(self, msg: str):
        # Reset with empty bytes
        self.response = (ctypes.c_char * CommandResponsePacket.NUM_RESP_CHARS)()
        # Set the maximum number of bytes we can
        lim = min(CommandResponsePacket.NUM_RESP_CHARS, len(msg))
        self.response[:lim] = msg[:lim].encode("utf-8")


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


# Define a unique ID for each packet type
PACKET_IDS = {
    HealthPacket: 0,
    QuicklookPacket: 1,
    CommandResponsePacket: 2
}
