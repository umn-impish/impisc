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
    Does no validation of the validation itself...
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
    valid = [0.2, 0.16, 1.4989561561, 3.1]
    for value in valid:
        device.idle_time = value
        expected = round(value, 1)
        assert expected == device.idle_time, (
            f"Expected {expected} but got {device.idle_time} instead (rounding error?)"
        )
    invalid = [0.01, 3.11]
    for value in invalid:
        try:
            device.idle_time = value
            raise RuntimeError("SHOULD NOT REACH HERE!!!")
        except ValueError:
            pass
    device.idle_time = 0.1


def test_os_mode():
    """Test changing the OS operation mode."""
    device = PCT2075(1, 0x49)
    device.wakeup()
    valid = ["comparator", "interrupt"]
    for mode in valid:
        device.os_mode = mode
        assert device.os_mode == mode
    invalid = ["garbage", 10]
    for value in invalid:
        try:
            device.os_mode = value
            raise RuntimeError("SHOULD NOT REACH HERE!!!")
        except ValueError:
            pass


def test_os_polarity():
    """Test changing the OS polarity."""
    device = PCT2075(1, 0x49)
    device.wakeup()
    valid = ["low", "high"]
    for pol in valid:
        device.os_polarity = pol
        assert device.os_polarity == pol
    invalid = ["garbage", 10]
    for value in invalid:
        try:
            device.os_polarity = value
            raise RuntimeError("SHOULD NOT REACH HERE!!!")
        except ValueError:
            pass


def test_os_queue():
    """Test changing the OS fault queue."""
    device = PCT2075(1, 0x49)
    device.wakeup()
    valid = [1, 2, 4, 6]
    for value in valid:
        device.os_queue = value
        assert (device.os_queue) == value
    invalid = [-1, 0.5, 1000, "garbage"]
    for value in invalid:
        try:
            device.os_queue = value
            raise RuntimeError("SHOULD NOT REACH HERE!!!")
        except ValueError:
            pass


def test_overtemperature_threshold():
    device = PCT2075(1, 0x49)
    device.wakeup()
    for value in [-55, -25, -0.5, 0, 0.5, 25, 80, 125]:
        device.overtemperature_threshold = value
        print(device.overtemperature_threshold)
        assert device.overtemperature_threshold == value
    device.overtemperature_threshold = 80


def test_hysteresis_temperature():
    device = PCT2075(1, 0x49)
    device.wakeup()
    for value in [-55, -25, -0.5, 0, 0.5, 25, 80, 125]:
        device.hysteresis_temperature = value
        print(device.hysteresis_temperature)
        assert device.hysteresis_temperature == value
    device.hysteresis_temperature = 75
