"""
Basic tests for the PCT2075 temperature sensor.
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


if __name__ == '__main__':
    test_shutdown()
