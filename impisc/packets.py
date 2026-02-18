import ctypes


class QuicklookPacket(ctypes.LittleEndianStructure):
    """
    """

    # Do not include padding bytes
    _pack_ = 1

    _fields_ = [
        ("unix_timestamp", ctypes.c_uint32),
        ("det1_ebin1", ctypes.c_uint8),
        ("det1_ebin1_counts", ctypes.c_uint16),
        ("det1_ebin1_cps", ctypes.c_uint16),
        ("det1_ebin2", ctypes.c_uint8),
        ("det1_ebin2_counts", ctypes.c_uint16),
        ("det1_ebin2_cps", ctypes.c_uint16),
        ("det1_ebin3", ctypes.c_uint8),
        ("det1_ebin3_counts", ctypes.c_uint16),
        ("det1_ebin3_cps", ctypes.c_uint16),
        ("det1_ebin4", ctypes.c_uint8),
        ("det1_ebin4_counts", ctypes.c_uint16),
        ("det1_ebin4_cps", ctypes.c_uint16),

        ("det2_ebin1", ctypes.c_uint8),
        ("det2_ebin1_counts", ctypes.c_uint16),
        ("det2_ebin1_cps", ctypes.c_uint16),
        ("det2_ebin2", ctypes.c_uint8),
        ("det2_ebin2_counts", ctypes.c_uint16),
        ("det2_ebin2_cps", ctypes.c_uint16),
        ("det2_ebin3", ctypes.c_uint8),
        ("det2_ebin3_counts", ctypes.c_uint16),
        ("det2_ebin3_cps", ctypes.c_uint16),
        ("det2_ebin4", ctypes.c_uint8),
        ("det2_ebin4_counts", ctypes.c_uint16),
        ("det2_ebin4_cps", ctypes.c_uint16),

        ("det3_ebin1", ctypes.c_uint8),
        ("det3_ebin1_counts", ctypes.c_uint16),
        ("det3_ebin1_cps", ctypes.c_uint16),
        ("det3_ebin2", ctypes.c_uint8),
        ("det3_ebin2_counts", ctypes.c_uint16),
        ("det3_ebin2_cps", ctypes.c_uint16),
        ("det3_ebin3", ctypes.c_uint8),
        ("det3_ebin3_counts", ctypes.c_uint16),
        ("det3_ebin3_cps", ctypes.c_uint16),
        ("det3_ebin4", ctypes.c_uint8),
        ("det3_ebin4_counts", ctypes.c_uint16),
        ("det3_ebin4_cps", ctypes.c_uint16),

        ("det4_ebin1", ctypes.c_uint8),
        ("det4_ebin1_counts", ctypes.c_uint16),
        ("det4_ebin1_cps", ctypes.c_uint16),
        ("det4_ebin2", ctypes.c_uint8),
        ("det4_ebin2_counts", ctypes.c_uint16),
        ("det4_ebin2_cps", ctypes.c_uint16),
        ("det4_ebin3", ctypes.c_uint8),
        ("det4_ebin3_counts", ctypes.c_uint16),
        ("det4_ebin3_cps", ctypes.c_uint16),
        ("det4_ebin4", ctypes.c_uint8),
        ("det4_ebin4_counts", ctypes.c_uint16),
        ("det4_ebin4_cps", ctypes.c_uint16),
    ]
    
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
