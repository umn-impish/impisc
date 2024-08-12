'''
Here are definitions of IMPISH packets which we
will receive from the balloon and send down to
the ground.

Some definitions may be located in different libraries,
such as the science data packets.

Doesn't really matter as long as we enumerate them all here!
'''
import ctypes
from umndet.common import impress_exact_structs as ies

# Helper type to be used here and elsewhere
CommandCharArray = ctypes.c_ubyte * 1024

class ArbitraryLinuxCommand(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = (
        # Allow a 1KiB string of text to be passed
        ('command', CommandCharArray),
    )


class ArbitraryLinuxCommandResponse(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = (
        # Split the command response up into
        # 1 KiB chunks which will get re-aligned by GSE
        ('response', CommandCharArray),
        ('seq_num', ctypes.c_ubyte)
    )

all_commands = [
    ArbitraryLinuxCommand,
]

all_telemetry_packets = [
    ArbitraryLinuxCommandResponse,
    ies.DetectorHealth,
]