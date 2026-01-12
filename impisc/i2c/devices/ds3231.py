"""
Defines a class for interfacing with the DS3231 RTC module
from Analog Devices. We will be using its PPS function.
"""

import os
import time

from .device import GenericDevice, Register


class DS3231(GenericDevice):
    """Interface with a connected DS3231 device."""

    def __init__(self, bus_number: int, address: int):
        super().__init__(bus_number=bus_number, address=address)
        self.add_register(Register("control", 0x0E, 8))
        self.add_register(Register("status", 0x0F, 8))
        self.give_to_kernel()

    @property
    def busy(self) -> bool:
        """Check if the device is busy."""
        return ((self.read_block_data("status") & 1) << 2) != 0

    @property
    def pps_enabled(self) -> bool:
        """Check if the PPS is enabled."""
        return (self.read_block_data("control") & 0b00011100) == 0

    @property
    def control_register(self) -> int:
        """The current state of the control register."""
        return self.read_block_data("control")

    @property
    def kernel_control(self) -> bool:
        """Returns whether the DS3231 is currently controlled by the kernel
        by checking for the presence of the "driver" symlink for the device.
        """
        return os.path.exists(
            f"/sys/bus/i2c/devices/i2c-1/{self.bus_number}-{self.address:04x}/driver"
        )

    def enable_pps(self) -> None:
        """Enables the PPS."""
        self.write_block_data("control", self.control_register & 0b11100011)
        self._pps_enabled = True

    def disable_pps(self) -> None:
        """Disables the PPS."""
        self.write_block_data("control", self.control_register | 0b00000100)
        self._pps_enabled = False

    def toggle_pps(self) -> bool:
        """Returns the **new** state of the PPS."""
        if self.pps_enabled:
            self.disable_pps()
        else:
            self.enable_pps()

        return self.pps_enabled

    def read_temperature(self) -> float:
        """Temperature in degrees celsius.
        TODO: Add in LSB?
        """
        self._force_convert()
        byte_tmsb = self.read_data(0x11)
        self.read_data(0x12)
        tinteger = (byte_tmsb & 0x7F) + ((byte_tmsb & 0x80) >> 7) * -(2**8)
        tdecimal = (byte_tmsb >> 7) * 2 ** (-1) + ((byte_tmsb & 0x40) >> 6) * 2 ** (-2)

        return tinteger + tdecimal

    def _force_convert(self):
        """Force a conversion and wait until it completes.
        This forces an update to the registers storing the temperature.
        """
        while self.busy:
            time.sleep(0.1)
        CONV = 0b00100000  # 32
        if not (self.control_register & CONV):
            self.write_block_data("control", self.control_register | CONV)
        while self.control_register & CONV:
            while self.busy:
                time.sleep(0.1)
            # Reduce CPU usage by sleeping; the device
            # takes a while to perform the conversion anyway
            time.sleep(0.1)

    def give_to_kernel(self, quiet: bool = True):
        """Gives the DS3231 to the Linux Kernel.
        A delay of 0.5 s is added to give the system enough time to update.
        """
        if self.kernel_control:
            return
        if not quiet:
            print(f"Adding rtc_ds1307 to kernel.")
        with open("/sys/bus/i2c/drivers/rtc-ds1307/bind", "w") as f:
            f.write(f"{self.bus_number}-{self.address:04x}")
        while not self.kernel_control:
            time.sleep(0.001)  # Reduced CPU usage compared to pass

    def release_from_kernel(self, quiet: bool = True):
        """Releases the DS3231 from the Linux Kernel.
        A delay of 0.5 s is added to give the system enough time to update.
        This value of 0.5 is empirical...
        """
        if not self.kernel_control:
            return
        if not quiet:
            print(f"Releasing rtc_ds1307 from kernel.")
        with open("/sys/bus/i2c/drivers/rtc-ds1307/unbind", "w") as f:
            f.write(f"{self.bus_number}-{self.address:04x}")
        while self.kernel_control:
            time.sleep(0.001)  # Reduced CPU usage compared to pass

    def __del__(self):
        """Return device to kernel upon destruction."""
        self.give_to_kernel()