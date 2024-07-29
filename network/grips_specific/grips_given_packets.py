'''
Packet (header) definitions to send/receive from GRIPS.

There are headers for commands and telemetry that we have to follow.
There is also a standard packet for acknowledging commands.

Science and housekeeping packets need to be indicated
via the fields in the telemetry command.

GRIPS network documentation available on IMPISH shared GDrive in Resources folder.
'''

import ctypes

GRIPS_PACKING = 1

# Copy the SMASH system ID
IMPISH_SYSTEM_ID = 0xC0


class BaseHeader(ctypes.LittleEndianStructure):
    '''Header info shared between GRIPS packet headers.'''
    _pack_ = GRIPS_PACKING
    _fields_ = (
        ('sync', ctypes.c_uint16),
        ('checksum_crc16', ctypes.c_uint16),
        ('system_id', ctypes.c_uint8),
    )
    def __init__(self):
        self.system_id = IMPISH_SYSTEM_ID
        self.sync = 0xEB90


class CommandHeader(ctypes.LittleEndianStructure):
    _pack_ = GRIPS_PACKING
    _fields_ = (
        ('base_header', BaseHeader),
        ('cmd_type', ctypes.c_uint8),
        ('counter', ctypes.c_uint8),
        ('size', ctypes.c_uint8)
    )


class GondolaTime(ctypes.LittleEndianStructure):
    _pack_ = GRIPS_PACKING
    _fields_ = (
        # Gondola time is stored in 48B,
        # little endian
        ('_gondola_ls32', ctypes.c_uint32),
        ('_gondola_ms16', ctypes.c_uint16)
    )

    def compute(self):
        '''Gondola time is 48 bytes so build it up
        from defined fields.'''
        return (
             int(self._gondola_ls32) | 
            (int(self._gondola_ms16) << 32)
        )


class TelemetryHeader(ctypes.LittleEndianStructure):
    _pack_ = GRIPS_PACKING
    _fields_ = (
        ('base_header', BaseHeader),

        # 0x02 to 0x0F = housekeeping
        # 0x10 to 0xFF = science
        ('telem_type', ctypes.c_uint8),

        ('size', ctypes.c_uint16),
        ('counter', ctypes.c_uint8),
        ('_gondola_time', GondolaTime),
    )

    def __init__(self):
        self.sync = 0xEB90

    @property
    def gondola_time(self):
        return self._gondola_time.compute() 


ErrorData = ctypes.c_uint8 * 7
class CommandAcknowledgement(ctypes.LittleEndianStructure):

    # Taken from command def. document
    NO_ERROR = 0
    PARTIAL_HEADER = 1
    INVALID_SYNC = 2
    INCORRECT_CRC = 3
    INCORRECT_SYSTEM_ID = 4
    INVALID_COMMAND_TYPE = 5
    INCORRECT_PACKET_LENGTH = 6
    INVALID_PACKET_LENGTH = 7
    INVALID_PAYLOAD_VALUE = 8
    BUSY = 9
    GENERAL_FAILURE = 10

    _pack_ = GRIPS_PACKING
    _fields_ = (
        ('base_header', BaseHeader),
        ('telem_type', ctypes.c_uint8),
        ('size', ctypes.c_uint16),
        ('counter', ctypes.c_uint8),
        ('cmd_type', ctypes.c_uint8),
        ('_gondola_time', GondolaTime),
        ('error_type', ctypes.c_uint8),
        ('error_data', ErrorData),
    )

    def __init__(self):
        # Telemetry type is fixed
        self.telem_type = 1
        # Size is fixed (type + data)
        self.size = 8

        # Default to no error
        self.error_type = 0
        self.error_data = ErrorData(*([0] * 7))

    @property
    def gondola_time(self):
        return self._gondola_time.compute() 


class CrcError(ValueError):
    pass


def apply_crc16(packet_bytes: bytearray) -> None:
    '''Generate the CRC16 checksum for a given GRIPS packet'''
    head = BaseHeader.from_buffer_copy(packet_bytes)

    # Zero out the CRC before computing
    head.checksum_crc16 = 0
    head.checksum_crc16 = compute_modbus_crc16(packet_bytes)


def verify_crc16(packet_bytes: bytearray) -> None:
    # Header from a writable buffer
    head = BaseHeader.from_buffer(packet_bytes)

    # Get a copy of the CRC
    stored_crc = int(head.checksum_crc16)
    head.checksum_crc16 = 0

    computed_crc = int(compute_modbus_crc16(packet_bytes)) 

    # Restore original CRC back to packet bytes
    head.checksum_crc16 = stored_crc

    if stored_crc != computed_crc:
        raise CrcError("CRC for packet invalid")


def compute_modbus_crc16(msg: bytearray | bytes) -> ctypes.c_uint16:
    '''https://stackoverflow.com/a/75328573/4333515'''
    crc = 0xFFFF
    for n in range(len(msg)):
        crc ^= msg[n]
        for i in range(8):
            if crc & 1:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return ctypes.c_uint16(crc)

