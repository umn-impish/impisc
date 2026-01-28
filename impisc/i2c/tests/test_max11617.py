"""
Tests the functionality of the MAX11617 device class.
"""

import pytest

from impisc.i2c.devices.max11617 import MAX11617


def get_device() -> MAX11617:
    """Return the device at the pre-defined address."""
    return MAX11617(1, 0x35)


def test_reference():
    """Test setting and reading the reference voltage source."""
    device: MAX11617 = get_device()
    mapped = {
        "vdd": 0b10000010,
        "external": 0b10100010,
        "internal":0b11010010
    }
    for ref, byte in mapped.items():
        device.reference = ref
        assert device.reference == ref
        assert device.setup_register == byte
    for ref in [1, "garbage", False]:
        with pytest.raises(ValueError):
            device.reference = ref


def test_external_clock():
    """Test setting and reading the reference voltage source."""
    device: MAX11617 = get_device()
    mapped = {
        False: 0b10000010,
        True: 0b10001010
    }
    for clock, byte in mapped.items():
        device.external_clock = clock
        assert device.external_clock == clock
        assert device.setup_register == byte
    for clock in [2, "garbage", 0.1]:
        with pytest.raises(ValueError):
            device.external_clock = clock


def test_bipolar():
    """Test setting and reading the polarity."""
    device: MAX11617 = get_device()
    mapped = {
        True: 0b10000110,
        False: 0b10000010
    }
    for bipolar, byte in mapped.items():
        device.bipolar = bipolar
        assert device.bipolar == bipolar
        assert device.setup_register == byte
    for bipolar in [2, "garbage", 0.1]:
        with pytest.raises(ValueError):
            device.bipolar = bipolar


def test_scan():
    """Test setting and reading the scan value."""
    device: MAX11617 = get_device()
    mapped = {
        0: 0b00000001,
        1: 0b00100001,
        2: 0b01000001,
        3: 0b01100001
    }
    for scan, byte in mapped.items():
        device.scan = scan
        assert device.scan == scan
        assert device.config_register == byte
    for scan in ["garbage", 1.2, 100, -1]:
        with pytest.raises(ValueError):
            device.scan = scan


def test_channel():
    """Test setting and reading the channel value."""
    device: MAX11617 = get_device()
    mapped = {c: 1 + (c << 1) for c in range(0, 12)}
    for chan, byte in mapped.items():
        device.channel = chan
        assert device.channel == chan
        assert device.config_register == byte
    for chan in [-1, "garbage", 1.2]:
        with pytest.raises(ValueError):
            device.channel = chan


def test_single_ended():
    """Test setting the single-ended and differential measurements."""
    device: MAX11617 = get_device()
    mapped = {
        False: 0b00000000,
        True: 0b00000001
    }
    for single_ended, byte in mapped.items():
        device.single_ended = single_ended
        assert device.single_ended == single_ended
        assert device.config_register == byte
    for single_ended in [-1, "garbage", 0.0001]:
        with pytest.raises(ValueError):
            device.single_ended = single_ended


def test_conversion():
    """Test reading a conversion from the device."""
    device: MAX11617 = get_device()
    device.reference = "internal"
    for chan in range(0, 12):
        conv = device.read_conversion(which=chan)
        assert device.channel == chan
        assert (conv > -5) & (conv < 5)
    # If reference is not "internal", the vref arg must be specified
    for ref in ["external", "vdd"]:
        device.reference = ref
        with pytest.raises(ValueError):
            device.read_conversion(0, vref=None)
    # Test garbage inputs
    device.reference = "internal"
    for chan in [-1, "garbage", 23.5]:
        with pytest.raises(ValueError):
            device.read_conversion(which=chan)


def test_reset_registers():
    """Test resetting the registers to their default values."""
    device: MAX11617 = get_device()
    initial_setup = device.setup_register
    initial_config = device.config_register
    device.reference = "internal"
    assert initial_setup != device.setup_register
    assert initial_config == device.config_register
    device.reset_registers()
    assert initial_setup == device.setup_register
