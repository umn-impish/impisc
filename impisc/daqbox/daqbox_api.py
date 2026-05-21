import json
import struct
import pathlib
from time import sleep
import socket

# Command definitions
BLANK_COMMAND = bytes([0xFF, 0x10]) + bytes([0] * 30)
START = bytearray(BLANK_COMMAND)
START[3] = 1
STOP = bytearray(BLANK_COMMAND)
STOP[3] = 2

START_BASELINE_CALIBRATION = bytearray(BLANK_COMMAND)
START_BASELINE_CALIBRATION[3] = 0x07
END_BASELINE_CALIBRATION = bytearray(BLANK_COMMAND)
END_BASELINE_CALIBRATION[3] = 0x08

# Discriminate between waveform vs. spectrum packets
WAVEFORM_HEADER = bytes([0xAA, 0x55])


class DaqBoxConfig:
    _SAVE_ATTRS = (
        "thresholds",
        "enabled",
        "polarities",
        "zoom_division",
        "enable_pileup_rejection",
        "acquisition_mode",
        "integration_window",
        "pileup_integration_time",
    )

    @classmethod
    def from_file(cls, fn: pathlib.Path):
        """Read a JSON dump of the configuration into a Python object"""
        ret = cls()
        # The file is expected to contain a JSON dump of the object
        with open(fn, "r") as f:
            saved = json.load(f)

        for attr in DaqBoxConfig._SAVE_ATTRS:
            assert hasattr(ret, attr)
            setattr(ret, attr, saved[attr])
        return ret

    def __init__(self):
        # in 0.5 mV units
        self.thresholds = [50, 50, 50, 50]
        # Channels (3, 2, 1, 0)
        self.enabled = 0b0000
        # Polarities for (3, 2, 1, 0). 1 = positive, 0 = negative
        self.polarities = 0b1111
        # Integer (?) still unsure what it does
        self.zoom_division = 0
        self.enable_pileup_rejection = False
        # waveform or spectral mode
        self.acquisition_mode = "spectrum"
        # In 8ns time steps
        self.integration_window = 42
        # In 8ns time steps
        self.pileup_integration_time = 20

    def to_file(self, fn: pathlib.Path) -> None:
        """Dump the current configuration to a JSON file"""
        output = {a: getattr(self, a) for a in DaqBoxConfig._SAVE_ATTRS}
        with open(fn, "w") as f:
            json.dump(output, f)

    def to_packet(self) -> bytes:
        """Convert the configuration object into the proper 32B packet"""

        def pack_12bit_be(values):
            v0, v1, v2, v3 = values
            x = (v0 << 36) | (v1 << 24) | (v2 << 12) | v3
            return x.to_bytes(6, "big")

        packet = bytearray(BLANK_COMMAND)
        packet[15] = self.zoom_division & 0xFF
        packet[16] = self.enable_pileup_rejection
        packet[17:22] = pack_12bit_be(reversed(self.thresholds))
        packet[23] = 1 if self.acquisition_mode == "waveform" else 0
        packet[26] = self.enabled
        packet[27] = self.polarities
        packet[28:30] = struct.pack("!H", self.integration_window)
        packet[30:] = struct.pack("!H", self.pileup_integration_time)
        return bytes(packet)


class DaqBoxInterface:
    DATA_PACKET_SIZE = 8000
    HANDSHAKE_PACKET_SIZE = 1024

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("192.168.0.3", 8080))
        self.sock.setblocking(False)
        try:
            self.send(STOP, expect_handshake=False)
            self.flush()
        except BlockingIOError:
            pass

    def send(self, cmd: bytes | bytearray, expect_handshake: bool = True) -> bytes:
        DAQ_BOX_ADDR = ("192.168.0.2", 8080)
        self.sock.sendto(cmd, DAQ_BOX_ADDR)
        # Box expects a delay after each command sent to it
        sleep(0.2)
        if expect_handshake:
            handshake = self.recv()
            if len(handshake) != DaqBoxInterface.HANDSHAKE_PACKET_SIZE:
                raise ValueError("DAQBOX handshake not received; sync error?")
        else:
            self.flush()

    def recv(self) -> bytes:
        return self.sock.recv(DaqBoxInterface.DATA_PACKET_SIZE)

    def flush(self, max_iterations: int | None = None) -> None:
        max_iterations = max_iterations or 10_000
        for _ in range(max_iterations):
            try:
                self.sock.recv(DaqBoxInterface.DATA_PACKET_SIZE)
            except BlockingIOError:
                # Socket has been flushed
                break

    def recalibrate_baseline(self):
        self.send(START_BASELINE_CALIBRATION)
        sleep(0.1)
        return self.send(END_BASELINE_CALIBRATION)


def parse_waveform_packet(data: bytes):
    """Parse a waveform packet into its constituent data, as defined by the E&T standard"""
    if data[:2] != bytes([0xAA, 0x55]):
        raise ValueError("This is not a waveform packet")

    channel = data[2]
    if channel > 3:
        raise ValueError("Channel invalid from waveform packet")

    # The timestamp is a 5B value stored in big endian
    timestamp = 0
    ts_stop = (ts_start := 3) + 5
    for idx in range(ts_start, ts_stop):
        timestamp |= data[idx] << (8 * (ts_stop - idx))

    # The rest of the packet is just the data points; 996 of them
    points_end = 2000
    raw_data_points = struct.unpack("!996H", data[ts_stop:points_end])
    data_points = [0.5 * (dp if dp < 2048 else (dp - 4096)) for dp in raw_data_points]

    return {"channel": channel, "timestamp": timestamp, "data": data_points}


def parse_spectrum_packet(packet: bytes):
    """Parse a spectrum packet into a set of histograms, as defined by the E&T standard"""
    histograms = [list() for _ in range(4)]
    for i in range(0, DaqBoxInterface.DATA_PACKET_SIZE, 8):
        histograms[0].append(packet[i + 0] * 256 + packet[i + 1])
        histograms[1].append(packet[i + 2] * 256 + packet[i + 3])
        histograms[2].append(packet[i + 4] * 256 + packet[i + 5])
        histograms[3].append(packet[i + 6] * 256 + packet[i + 7])
    return histograms
