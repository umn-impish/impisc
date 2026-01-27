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
        ("bubba_output_volts", ctypes.c_int16),
        ("bubba_wiper", ctypes.c_uint8),
        # Power toggle status byte
        ("toggle_byte", ctypes.c_uint8),
        # Disk usages in 10 MiB units
        ("os_disk_usage", ctypes.c_uint16),
        ("data_disk_usage", ctypes.c_uint16),
        # Padding on the end of the health packet:
        # remove bytes from this as needed
        # to add packet fields after flight starts.
        ("extra", EXTRA_BYTES * ctypes.c_uint8),
        # Missing fields: one bit per field missing, in order
        ("missing_fields", ctypes.c_uint16),
    ]
