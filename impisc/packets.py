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
