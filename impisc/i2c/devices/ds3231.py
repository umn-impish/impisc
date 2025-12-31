"""
Defines a class for interfacing with the DS3231 RTC module
from Analog Devices. We will be using its PPS function.
"""

import time

from .device import GenericDevice, Register


class DS3231(GenericDevice):
    """Interface with a connected DS3231 device."""

    def __init__(self, bus_number: int, address: int):
        super().__init__(
            bus_number=bus_number, address=address, kernel_driver="rtc_ds1307"
        )
        self.add_register(Register("control", 0x0E, 8))
        self.add_register(Register("status", 0x0F, 8))
        time.sleep(1)  # Is this needed?
        self.release_from_kernel(quiet=False)
        self.disable_pps()
        self._pps_enabled = False
        self.give_to_kernel(quiet=False)

    @property
    def busy(self) -> bool:
        """Check if the device is busy."""
        return ((self.read_block_data("status") & 1) << 2) != 0

    @property
    def pps_enabled(self) -> bool:
        """Check if the PPS is enabled."""
        return self._pps_enabled

    @property
    def control_register(self) -> int:
        """The current state of the control register."""
        return self.read_block_data("control")

    def enable_pps(self) -> None:
        """Enables the PPS."""
        self.write_block_data("control", self.control_register & 0b11100011)
        self._pps_enabled = True

    def disable_pps(self) -> None:
        """Disables the PPS."""
        self.write_block_data("control", self.control_register | 0b00011100)
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
            pass
        CONV = 0b00100000  # 32
        if self.control_register & CONV == 0:
            self.write_data(0x0E, self.control_register | CONV)
        while self.control_register & CONV != 0:
            while self.busy:
                pass
            self.read_block_data("control")
