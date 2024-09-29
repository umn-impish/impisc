'''
Here are definitions of IMPISH packets which we
will receive from the balloon and send down to
the ground.

Some definitions may be located in different libraries,
such as the science data packets.

Doesn't really matter as long as we enumerate them all here!
'''
from dataclasses import dataclass
import ctypes
from umndet.common import impress_exact_structs as ies


@dataclass
class CmdHeader(ctypes.LittleEndianStructure):
    '''
    Header data that we attach to every command packet.
    Command replies are sent directly back to the 
    commander, but auxiliary data we may want to
    forward elsewhere, e.g. a udp_capture or straight
    back to the ground via a separate process.
    '''
    telemeter_port: int


CommandCharArray = ctypes.c_ubyte * 255
class ArbitraryLinuxCommand(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = (
        ('command', CommandCharArray),
    )


ResponseCharArray = ctypes.c_ubyte * 1024
class ArbitraryLinuxCommandResponse(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = (
        # Split the command response up into
        # 1 KiB chunks which will get re-aligned by GSE
        ('response', ResponseCharArray),
        ('seq_num', ctypes.c_ubyte)
    )


class DummyCmd(ctypes.LittleEndianStructure):
    pass


class Dummy(ctypes.LittleEndianStructure):
    '''Test struct'''
    _pack_ = 1
    _fields_ = (
        ('data', ctypes.c_ubyte * 256),
    )

all_commands = [
    ArbitraryLinuxCommand,
    DummyCmd,
]

all_telemetry_packets = [
    ArbitraryLinuxCommandResponse,
    Dummy,
    ies.DetectorHealth,
]