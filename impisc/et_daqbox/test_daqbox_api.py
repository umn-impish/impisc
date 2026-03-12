from impisc.et_daqbox import daq_box_api as dbapi
import tempfile
import pathlib
import pytest


@pytest.fixture
def dbox_iface():
    return dbapi.DaqBoxInterface()


def test_config_to_from_file():
    """Test if we can save/read DAQBOX config to a file"""
    cfg = dbapi.DaqBoxConfig()

    with tempfile.TemporaryDirectory() as tdn:
        out_file = pathlib.Path(tdn) / "config.json"
        cfg.to_file(out_file)

        other = dbapi.DaqBoxConfig.from_file(out_file)
        for k in other._SAVE_ATTRS:
            assert getattr(other, k) == getattr(cfg, k)


def test_waveform_acquisition(dbox_iface):
    cfg = dbapi.DaqBoxConfig()
    cfg.polarities = 0
    cfg.enabled = 1
    cfg.zoom_division = 4
    cfg.acquisition_mode = "waveform"

    iface = dbox_iface
    iface.send(cfg.to_packet())

    # Clear some of the waveforms
    iface.flush(max_iterations=10)

    iface.send(dbapi.START)
    iface.sock.setblocking(True)
    out = list()
    for i in range(200):
        wf = dbapi.parse_waveform_packet(iface.recv())
        out.append(wf["data"])
    iface.sock.setblocking(False)
    iface.send(dbapi.STOP, expect_handshake=False)


def test_spectrum_acquisition(dbox_iface):
    cfg = dbapi.DaqBoxConfig()
    # Configure the DAQ Box to take waveform data
    cfg.acquisition_mode = "spectrum"
    # Only enable channel 1
    cfg.enabled = 0b1111
    # Expect positive polarities on every channel
    cfg.polarities = 0b0000

    iface = dbox_iface
    iface.send(cfg.to_packet())

    per_second = 32
    total_spectra = per_second * 5

    spectra = list()
    iface.flush()
    iface.send(dbapi.START)
    iface.sock.setblocking(True)
    while len(spectra) < total_spectra:
        packet = iface.recv()
        if len(packet) == dbapi.DaqBoxInterface.HANDSHAKE_PACKET_SIZE:
            raise ValueError("captured a handshake?")
        spectra.append(packet)
