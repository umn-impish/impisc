"""
Tests the kernel control and PPS enabling/disabling/toggling for the
DS3231 device class.
"""

from impisc.i2c.devices.ds3231 import DS3231
import time


def test_kernel_control():
    """Test the kernel control conditions."""
    device = DS3231(1, 0x68)
    assert device.kernel_control, "Kernel should have control by default"

    # Test private method functionality.
    device._release_from_kernel()  # pyright: ignore[reportPrivateUsage]
    assert not device.kernel_control
    device._release_from_kernel()  # pyright: ignore[reportPrivateUsage]
    assert not device.kernel_control
    device._give_to_kernel()  # pyright: ignore[reportPrivateUsage]
    assert device.kernel_control
    device._release_from_kernel()  # pyright: ignore[reportPrivateUsage]
    assert not device.kernel_control

    # Test context manager.
    with device.release_from_kernel():
        assert not device.kernel_control
    assert device.kernel_control

    # Test that the context manager handles exceptions
    try:
        with device.release_from_kernel():
            raise RuntimeError()
    except RuntimeError:
        pass
    finally:
        assert device.kernel_control


def test_pps():
    """Test toggling the PPS; ensures enabling/disabling/toggling."""
    device = DS3231(1, 0x68)
    with device.release_from_kernel():
        starting_state = device.pps_enabled
        _ = device.toggle_pps()
        assert starting_state != device.pps_enabled, "PPS toggle failed"
        _ = device.toggle_pps()
        assert starting_state == device.pps_enabled

        device.disable_pps()
        assert not device.pps_enabled

        device.enable_pps()
        assert device.pps_enabled

        device.disable_pps()
        device.disable_pps()
        assert not device.pps_enabled

        device.enable_pps()
        device.enable_pps()
        assert device.pps_enabled


def test_temperature():
    """Test reading the temperature from the device."""
    device = DS3231(1, 0x68)
    with device.release_from_kernel():
        initial_temp = device.read_temperature()
        assert -50 < initial_temp < 100
        time.sleep(0.5)
        for _ in range(3):
            t = device.read_temperature()
            # Assume the temperature doesn't change much
            # during the loop iterations
            assert abs(t - initial_temp) < 1


def test_responsive():
    """Test the responsiveness of the device."""
    device = DS3231(1, 0x68)
    assert not device.responsive  # Under kernel control
    with device.release_from_kernel():
        assert device.responsive
    assert not device.responsive  # Under kernel control
