from impisc.i2c.devices.ds3231 import DS3231


def test_kernel_control():
    """Test the kernel control conditions."""
    device = DS3231(1, 0x68)
    assert device.kernel_control, "Kernel should have control by default"
    device.release_from_kernel()
    assert not device.kernel_control
    device.release_from_kernel()
    assert not device.kernel_control
    device.give_to_kernel()
    assert device.kernel_control


def test_pps():
    """Test toggling the PPS; ensures enabling/disabling/toggling."""
    device = DS3231(1, 0x68)
    device.release_from_kernel()

    starting_state = device.pps_enabled
    device.toggle_pps()
    assert starting_state != device.pps_enabled, "PPS toggle failed"
    device.toggle_pps()
    assert starting_state == device.pps_enabled

    device.enable_pps()
    assert device.pps_enabled

    device.disable_pps()
    assert not device.pps_enabled

    device.enable_pps()
    device.enable_pps()
    assert device.pps_enabled

    device.disable_pps()
    device.disable_pps()
    assert not device.pps_enabled


if __name__ == "__main__":
    test_pps()
