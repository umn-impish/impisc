"""
Tests the functionality of the MAX11617 device class.
"""

import pytest

from impisc.i2c.devices.max11617 import MAX11617


def get_device() -> MAX11617:
    """Return the device at the pre-defined address."""
    return MAX11617(1, 0x35)


def test_channel():
    """Test setting and reading the channel value."""
    device: MAX11617 = get_device()
    for chan in range(0, 12):
        device.channel = chan
        assert device.channel == chan
    for chan in [-1, "garbage", 1.2]:
        with pytest.raises(ValueError):
            device.channel = chan


def test_scan():
    """Test setting and reading the scan value."""
    device: MAX11617 = get_device()
    for scan in [0, 1, 2, 3]:
        device.scan = scan
        assert device.scan == scan
    for scan in ["garbage", 1.2, 100, -1]:
        with pytest.raises(ValueError):
            device.scan = scan


def test_reference():
    """Test setting and reading the reference voltage source."""
    device: MAX11617 = get_device()
    for ref in ["vdd", "external", "internal"]:
        device.reference = ref
        assert device.reference == ref
    for ref in [1, "garbage", False]:
        with pytest.raises(ValueError):
            device.reference = ref


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
