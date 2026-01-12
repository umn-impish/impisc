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
        assert expected == device.idle_time, f'Expected {expected} but got {device.idle_time} instead (rounding error?)'
    invalid = [0.01, 3.11]
    for value in invalid:
        try:
            device.idle_time = value
            raise RuntimeError('SHOULD NOT REACH HERE!!!')
        except ValueError:
            pass
    device.idle_time = 0.1
