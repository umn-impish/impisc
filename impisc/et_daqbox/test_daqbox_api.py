from impisc.et_daqbox import daq_box_api as dbapi
import tempfile
import pathlib


def test_config_to_from_file():
    """Test if we can save/read DAQBOX config to a file"""
    cfg = dbapi.DaqBoxConfig()

    with tempfile.TemporaryDirectory() as tdn:
        out_file = pathlib.Path(tdn) / "config.json"
        cfg.to_file(out_file)

        other = dbapi.DaqBoxConfig.from_file(out_file)
        for k in other._SAVE_ATTRS:
            assert getattr(other, k) == getattr(cfg, k)


def test_waveform_acquisition():
    # Configure the DAQ Box to take waveform data
    iface = dbapi.DaqBoxInterface()
    cfg = dbapi.DaqBoxConfig()
    cfg.acquisition_mode = "waveform"
    iface.send(cfg.to_packet())

    # Start taking waveform data
    iface.recalibrate_baseline()
    iface.send(dbapi.START)

    # Flush out the first ~100 waveforms in case any are erroneous
    iface.flush(max_iterations=128)

    waveforms = list()
    while len(waveforms) < 1000:
        pkt = iface.recv()
        if pkt[:2] == dbapi.WAVEFORM_HEADER:
            waveforms.append(dbapi.parse_waveform_packet(pkt))

    raise NotImplementedError("finish this test")
    ...


def test_spectrum_acquisition():
    cfg = dbapi.DaqBoxConfig()
    # Configure the DAQ Box to take waveform data
    cfg.acquisition_mode = "spectrum"
    # Only enable channel 1
    cfg.enabled = 0b1000
    # Expect positive polarities on every channel
    cfg.polarities = 0b1111

    iface = dbapi.DaqBoxInterface()
    iface.send(cfg.to_packet())

    per_second = 32
    total_spectra = per_second * 5

    spectra = list()
    iface.flush()
    iface.send(dbapi.START)
    while len(spectra) < total_spectra:
        spectra.append(dbapi.parse_spectrum_packet(iface.recv()))

    raise NotImplementedError("finish this test")
    ...
