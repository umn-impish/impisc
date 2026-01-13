"""
Basic tests for the PCT2075 temperature sensor. Tests:
- Shutdown/wakeup
- Temperature reading
- Idle time setting
"""

from impisc.i2c.devices.pct2075 import PCT2075


def test_shutdown():
    """Check that the device can be shutdown and woken up."""
    device = PCT2075(1, 0x49)
    starting_state = device.is_shutdown
    if starting_state:
        device.wakeup()
        assert not device.is_shutdown, "Failed to wakeup"
    else:
        device.shutdown()
        assert device.is_shutdown, "Failed to shutdown"

    device.shutdown()
    assert device.is_shutdown
    device.shutdown()
    assert device.is_shutdown

    device.wakeup()
    assert not device.is_shutdown
    device.wakeup()
    assert not device.is_shutdown


def test_temperature_reading():
    """Check that we receive a temperature from the device.
    Does no validation of the value itself...
    """
    device = PCT2075(1, 0x49)
    device.shutdown()
    device.read_temperature()
    device.wakeup()
    device.read_temperature()


def test_idle():
    """Test setting the idle time between temperature measurements."""
    device = PCT2075(1, 0x49)
    device.wakeup()
    device.idle_time = 0.1
    for value in [0.2, 0.16, 1.4989561561, 3.1, 0.1]:
        device.idle_time = value
        expected = round(value, 1)
        assert expected == device.idle_time, (
            f"Expected {expected} but got {device.idle_time} instead (rounding error?)"
        )
    for value in [0.01, 3.11]:
        try:
            device.idle_time = value
            raise RuntimeError("SHOULD NOT REACH HERE!!!")
        except ValueError:
            pass


def test_os_mode():
    """Test changing the OS operation mode."""
    device = PCT2075(1, 0x49)
    device.wakeup()
    for mode in ["interrupt", "comparator"]:
        device.os_mode = mode
        assert device.os_mode == mode
    for value in ["garbage", 10, ""]:
        try:
            device.os_mode = value
            raise RuntimeError("SHOULD NOT REACH HERE!!!")
        except ValueError:
            pass


def test_os_polarity():
    """Test changing the OS polarity."""
    device = PCT2075(1, 0x49)
    device.wakeup()
    for pol in ["high", "low"]:
        device.os_polarity = pol
        assert device.os_polarity == pol
    for value in ["garbage", 10, ""]:
        try:
            device.os_polarity = value
            raise RuntimeError("SHOULD NOT REACH HERE!!!")
        except ValueError:
            pass


def test_os_queue():
    """Test changing the OS fault queue."""
    device = PCT2075(1, 0x49)
    device.wakeup()
    for value in [2, 4, 6, 1]:
        device.os_queue = value
        assert (device.os_queue) == value
    for value in [-1, 0.5, 1000, "garbage"]:
        try:
            device.os_queue = value
            raise RuntimeError("SHOULD NOT REACH HERE!!!")
        except ValueError:
            pass


def test_overtemperature_threshold():
    device = PCT2075(1, 0x49)
    device.wakeup()
    for value in [-55, -25, -0.5, 0, 0.5, 25, 125, 80]:
        device.overtemperature_threshold = value
        assert device.overtemperature_threshold == value
    for value in [-100, 10000]:
        try:
            device.overtemperature_threshold = value
            raise RuntimeError("SHOULD NOT REACH HERE!!!")
        except ValueError:
            pass


def test_hysteresis_temperature():
    device = PCT2075(1, 0x49)
    device.wakeup()
    for value in [-55, -25, -0.5, 0, 0.5, 25, 125, 75]:
        device.hysteresis_temperature = value
        assert device.hysteresis_temperature == value
    for value in [-100, 10000]:
        try:
            device.hysteresis_temperature = value
            raise RuntimeError("SHOULD NOT REACH HERE!!!")
        except ValueError:
            pass
