"""
Basic tests for the PCT2075 temperature sensor. Tests:
- Shutdown/wakeup
- Temperature reading
- Idle time setting
- Overtemperature shutdown
"""

import pytest
from impisc.i2c.devices.pct2075 import PCT2075


def get_device():
    return PCT2075(1, 0x49)


def test_shutdown():
    """Check that the device can be shutdown and woken up."""
    device = get_device()
    starting_state = device.awake
    if starting_state:
        device.awake = False
        assert not device.awake, "Failed to shutdown"
    else:
        device.awake = True
        assert device.awake, "Failed to wakeup"
    device.awake = False
    assert not device.awake
    device.awake = False
    assert not device.awake
    device.awake = True
    assert device.awake
    device.awake = True
    assert device.awake


def test_temperature_reading():
    """Check that we receive a temperature from the device.
    Does no validation of the value itself...
    """
    device = get_device()
    device.awake = False
    device.read_temperature()
    device.awake = True
    device.read_temperature()


def test_idle():
    """Test setting the idle time between temperature measurements."""
    device = get_device()
    device.awake = True
    device.idle_time = 0.1
    for value in [0.2, 0.16, 1.4989561561, 3.1, 0.1]:
        device.idle_time = value
        expected = round(value, 1)
        assert expected == device.idle_time, (
            f"Expected {expected} but got {device.idle_time} instead (rounding error?)"
        )
    for value in [0.01, 3.11]:
        with pytest.raises(ValueError):
            device.idle_time = value


def test_os_mode():
    """Test changing the OS operation mode."""
    device = get_device()
    device.awake = True
    for mode in ["interrupt", "comparator"]:
        device.os_mode = mode
        assert device.os_mode == mode
    for value in ["garbage", 10, ""]:
        with pytest.raises(ValueError):
            device.os_mode = value


def test_os_polarity():
    """Test changing the OS polarity."""
    device = get_device()
    device.awake = True
    for pol in ["high", "low"]:
        device.os_polarity = pol
        assert device.os_polarity == pol
    for value in ["garbage", 10, ""]:
        with pytest.raises(ValueError):
            device.os_polarity = value


def test_os_queue():
    """Test changing the OS fault queue."""
    device = get_device()
    device.awake = True
    for value in [2, 4, 6, 1]:
        device.os_queue = value
        assert (device.os_queue) == value
    for value in [-1, 0.5, 1000, "garbage"]:
        with pytest.raises(ValueError):
            device.os_queue = value


def test_overtemperature_threshold():
    device = get_device()
    device.awake = True
    for value in [-55, -25, -0.5, 0, 0.5, 25, 125, 80]:
        device.overtemperature_threshold = value
        assert device.overtemperature_threshold == value
    for value in [-100, 10000]:
        with pytest.raises(ValueError):
            device.overtemperature_threshold = value


def test_hysteresis_temperature():
    device = get_device()
    device.awake = True
    for value in [-55, -25, -0.5, 0, 0.5, 25, 125, 75]:
        device.hysteresis_temperature = value
        assert device.hysteresis_temperature == value
    for value in [-100, 10000]:
        with pytest.raises(ValueError):
            device.hysteresis_temperature = value
