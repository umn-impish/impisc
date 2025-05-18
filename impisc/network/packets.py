"""
Here are definitions of IMPISH packets which we
will receive from the balloon and send down to
the ground.

Some definitions may be located in different libraries,
such as the science data packets.

Doesn't really matter as long as we enumerate them all here!
"""

import ctypes
from typing import Iterable
from umndet.common import impress_exact_structs as ies


GRIPS_PACKING = 1
GRIPS_SYNC = 0xEB90

IMPISH_SYSTEM_ID = 0xED


class BaseHeader(ctypes.LittleEndianStructure):
    """Header info shared between GRIPS packet headers."""

    _pack_ = GRIPS_PACKING
    _fields_ = (
        ("sync", ctypes.c_uint16),
        ("checksum_crc16", ctypes.c_uint16),
        ("system_id", ctypes.c_uint8),
    )

    def __init__(self, sys_id=None):
        self.system_id = sys_id or IMPISH_SYSTEM_ID
        self.sync = GRIPS_SYNC


class HasGondolaTime:
    def __init__(self):
        assert hasattr(self, "_gondola_time") and isinstance(
            self._gondola_time, GondolaTime
        )

    @property
    def gondola_time(self):
        return self._gondola_time.compute()

    @gondola_time.setter
    def gondola_time(self, new: int):
        self._gondola_time._gondola_ls32 = new & 0xFFFFFFFF
        self._gondola_time._gondola_ms16 = (new >> 32) & 0xFFFF


class CommandHeader(ctypes.LittleEndianStructure):
    _pack_ = GRIPS_PACKING
    _fields_ = (
        ("base_header", BaseHeader),
        ("cmd_type", ctypes.c_uint8),
        ("counter", ctypes.c_uint8),
        ("size", ctypes.c_uint8),
    )

    def __init__(self):
        self.base_header = BaseHeader()


class GondolaTime(ctypes.LittleEndianStructure):
    _pack_ = GRIPS_PACKING
    _fields_ = (
        # Gondola time is stored in 48B,
        # little endian
        ("_gondola_ls32", ctypes.c_uint32),
        ("_gondola_ms16", ctypes.c_uint16),
    )

    def compute(self):
        """Gondola time is 48 bytes so build it up
        from defined fields."""
        return int(self._gondola_ls32) | (int(self._gondola_ms16) << 32)


class TelemetryHeader(ctypes.LittleEndianStructure, HasGondolaTime):
    _pack_ = GRIPS_PACKING
    _fields_ = (
        ("base_header", BaseHeader),
        # 0x02 to 0x0F = housekeeping
        # 0x10 to 0xFF = science
        ("telem_type", ctypes.c_uint8),
        ("size", ctypes.c_uint16),
        ("counter", ctypes.c_uint16),
        ("_gondola_time", GondolaTime),
    )

    def __init__(self):
        self.base_header = BaseHeader()


class AcknowledgeError(Exception):
    def __init__(
        self,
        error_type: int,
        error_data: Iterable,
        cmd_source_addr: tuple[str, int],
        cmd_seq_num: int,
        cmd_type: type[ctypes.LittleEndianStructure],
    ):
        """Encapsulates data required for an error Ack reply as an exception."""
        self.type: int = error_type
        self.data: bytes = bytes(error_data)
        self.cmd_source_addr: tuple[str, int] = cmd_source_addr
        self.counter: int = cmd_seq_num
        self.cmd_type: type[ctypes.LittleEndianStructure] = cmd_type
        super().__init__()


ErrorData = ctypes.c_uint8 * 7


class CommandAcknowledgement(ctypes.LittleEndianStructure, HasGondolaTime):
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

    # Index the array by the error value
    # for a human-readable identifier.
    HUMAN_READABLE_FAILURES = [
        "NO_ERROR",
        "PARTIAL_HEADER",
        "INVALID_SYNC",
        "INCORRECT_CRC",
        "INCORRECT_SYSTEM_ID",
        "INVALID_COMMAND_TYPE",
        "INCORRECT_PACKET_LENGTH",
        "INVALID_PACKET_LENGTH",
        "INVALID_PAYLOAD_VALUE",
        "BUSY",
        "GENERAL_FAILURE",
    ]

    ERROR_BYTES = 7
    _pack_ = GRIPS_PACKING
    _fields_ = (
        ("base_header", BaseHeader),
        ("telem_type", ctypes.c_uint8),
        ("size", ctypes.c_uint16),
        ("counter", ctypes.c_uint8),
        ("cmd_type", ctypes.c_uint8),
        ("_gondola_time", GondolaTime),
        ("error_type", ctypes.c_uint8),
        ("error_data", ErrorData),
    )

    def __init__(self):
        self.base_header = BaseHeader()

        # Telemetry type is fixed
        self.telem_type = 1
        # Size is fixed (type + data)
        self.size = 8

        # Default to no error
        self.error_type = 0
        self.error_data = ErrorData(*([0] * self.ERROR_BYTES))

    def pre_send(self, cmd_seq_num: int, cmd_type: int):
        """Give data to the Ack packet which is required
        before sending it off.

        This _could_ be part of the constructor,
        but the packet is technically initialized after
        construction. In some cases it might make sense to
        assign this information post-instantiation anyway.
        So for now, it's a separate method.
        """
        self.cmd_type = cmd_type
        self.counter = cmd_seq_num

    @classmethod
    def from_err(cls, ack_err: AcknowledgeError):
        obj = cls()
        obj.error_type = ack_err.type
        for i in range(min(cls.ERROR_BYTES, len(ack_err.data))):
            obj.error_data[i] = ack_err.data[i]
        obj.counter = ack_err.counter
        obj.cmd_type = all_commands.index(ack_err.cmd_type)
        return obj


class CrcError(ValueError):
    def __init__(self, recvd, comp, *args, **kwargs):
        # Store received and computed CRC
        self.received = ctypes.c_uint16(recvd)
        self.computed = ctypes.c_uint16(comp)
        super().__init__(*args, **kwargs)


def apply_crc16(packet_bytes: bytearray) -> None:
    """Generate the CRC16 checksum for a given GRIPS packet"""
    head = BaseHeader.from_buffer(packet_bytes)

    # Zero out the CRC before computing
    head.checksum_crc16 = 0
    head.checksum_crc16 = compute_modbus_crc16(packet_bytes)


def verify_crc16(packet_bytes: bytearray) -> None:
    # Header from a writable buffer
    head = BaseHeader.from_buffer(packet_bytes)

    # Get a copy of the CRC
    stored_crc = int(head.checksum_crc16)
    head.checksum_crc16 = 0

    computed_crc = compute_modbus_crc16(packet_bytes)

    # Restore original CRC back to packet bytes
    head.checksum_crc16 = stored_crc

    if stored_crc != computed_crc:
        raise CrcError(stored_crc, computed_crc, "CRC for packet invalid")


def compute_modbus_crc16(msg: bytearray | bytes) -> ctypes.c_uint16:
    """https://stackoverflow.com/a/75328573/4333515"""
    crc = 0xFFFF
    for n in range(len(msg)):
        crc ^= msg[n]
        for i in range(8):
            if crc & 1:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc


CommandCharArray = ctypes.c_ubyte * 255


class ArbitraryLinuxCommand(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = (("command", CommandCharArray),)


class ArbitraryLinuxCommandResponse(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = (
        # Split the command response up into
        # 1 KiB chunks which will get re-aligned by GSE
        ("response", ctypes.c_ubyte * 128),
        ("seq_num", ctypes.c_uint16),
    )


class DummyCmd(ctypes.LittleEndianStructure):
    pass


class Dummy(ctypes.LittleEndianStructure):
    """Test struct"""

    _pack_ = 1
    _fields_ = (("data", ctypes.c_ubyte * 256),)


class UnknownCmd(ctypes.LittleEndianStructure):
    """An unknown command type, used for some
    "ack error" replies before the packet
    can get totally decoded."""

    pass


all_commands = [
    UnknownCmd,
    ArbitraryLinuxCommand,
    DummyCmd,
]

all_telemetry_packets = [
    Dummy,  # numbering starts at 1, so skip this
    CommandAcknowledgement,
    ArbitraryLinuxCommandResponse,
    ies.DetectorHealth,
]
