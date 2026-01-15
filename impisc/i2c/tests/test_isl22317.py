"""
Basic tests for the ISL22317 digital potentiometer. Tests:
- Shutdown/wakeup
- Wiper setting/reading
"""

from impisc.i2c.devices.isl22317 import ISL22317


def test_shutdown():
    """Tests the shutdown/wakeup setting of the device."""
    device = ISL22317(0, 0x28)
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


def test_wiper():
    """Tests wiper setting and getting."""
    device = ISL22317(0, 0x28)
    device.awake = True
    for value in [0, 10, 100, 127]:
        device.wiper = value
        assert device.wiper == value, f"Expected {value} but got {device.wiper} instead"
    for value in [-1, 0.1, 10000, 1293820138048]:
        try:
            device.wiper = value
            raise RuntimeError("SHOULD NOT REACH HERE!!!")
        except ValueError:
            pass


def test_fast_operations():
    """Make sure we're not reading/writing too quickly.
    Doing so will cause an OSError (remote I/O error).
    """
    device = ISL22317(0, 0x28)
    device.awake = True
    for _ in range(20):
        device.wiper = 0
        device.wiper
        device.mode
        device.precision_mode
        device.mode = "two-terminal"
        device.precision_mode = True


def test_mode():
    """Test changing the mode between two-terminal and three-terminal."""
    device = ISL22317(0, 0x28)
    starting_mode = device.mode
    if starting_mode == "two-terminal":
        device.mode = "three-terminal"
        assert device.mode == "three-terminal", (
            "Failed to change to three-terminal mode"
        )
    else:
        device.mode = "two-terminal"
        assert device.mode == "two-terminal", "Failed to change to two-terminal mode"
    try:
        device.mode = "garbage"
        raise RuntimeError("SHOULD NOT REACH HERE!!!")
    except ValueError:
        pass
    device.mode = "two-terminal"


def test_precision_mode():
    """Test turning on/off precision mode."""
    device = ISL22317(0, 0x28)
    starting_state = device.precision_mode
    if starting_state:
        device.precision_mode = False
        assert not device.precision_mode, "Failed to turn off precision mode"
    else:
        device.precision_mode = True
        assert device.precision_mode, "Failed to turn on precision mode"
    device.precision_mode = False
    assert not device.precision_mode
    device.precision_mode = False
    assert not device.precision_mode
    device.precision_mode = True
    assert device.precision_mode
    device.precision_mode = True
    assert device.precision_mode
