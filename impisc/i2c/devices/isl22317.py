"""
Defines a class for interfacing with a ISL22317 I2C digital potentiometer.
"""

import time

from .device import GenericDevice, Register


class ISL22317(GenericDevice):
    """Interface with a connected ISL22317 digital potentiometer."""

    def __init__(self, bus_number: int, address: int):
        super().__init__(bus_number=bus_number, address=address)
        self.add_register(Register("wiper", 0x00, 8))  # IVR, WR
        self.add_register(Register("mode", 0x01, 8))  # MSR
        self.add_register(Register("control", 0x02, 8))  # ACR

    @property
    def wiper(self) -> int:
        """The value stored in the wiper register (0x00).
        Valid values are integers within [0, 127].
        """
        return self.read_block_data("wiper")

    @wiper.setter
    def wiper(self, value: int):
        """Writes the provided value to the wiper register.
        value must be an integer within [0, 127].
        Values outside this range raises a ValueError.
        """
        if value not in range(0, 128):
            raise ValueError(
                f"Provided wiper value ({value}) outside valid  range: [0, 127]"
            )
        while self.writing:
            time.sleep(0.005)
        self.write_block_data("wiper", value)
        time.sleep(0.05)
        # Trying to interface (read/write) with the device immediately
        # after writing causes a remote I/O error, so we sleep.

    @property
    def mode_register(self) -> int:
        """The current value of the mode register (MSR; 0x01)."""
        return self.read_block_data("mode")

    @property
    def control_register(self) -> int:
        """The current value of the control register (ACR; 0x02)."""
        return self.read_block_data("control")

    @property
    def awake(self) -> bool:
        """Specfies whether the device is awake (True) or shutdown (False)
        by reading the SHDN bit in the control register.
        """
        return bool((self.read_block_data("control") >> 6) & 1)

    @awake.setter
    def awake(self, state: bool):
        """Set the device to be awake (True) or shutdown (False)."""
        if state:
            self.write_block_data("control", self.control_register | 0b01000000)
        else:
            self.write_block_data("control", self.control_register & 0b10111111)

    @property
    def writing(self) -> bool:
        """Returns the value of the WIP bit in the access control register (0x02).
        True means a non-volatile write operation is in progress, meaning
        the wiper and control registers cannot be written to.
        """
        return bool((self.control_register >> 5) & 1)

    @property
    def mode(self) -> str:
        """The device mode, either two-terminal (rheostat) or
        three-terminal (voltage divier).
        """
        bit = (self.mode_register >> 7) & 1
        return "three-terminal" if bit else "two-terminal"

    @mode.setter
    def mode(self, new_mode: str):
        """Set the mode of the device; either "two-terminal" or "three-terminal"."""
        match new_mode:
            case "two-terminal":
                self.write_block_data("mode", self.mode_register & 0b01111111)
            case "three-terminal":
                self.write_block_data("mode", self.mode_register | 0b10000000)
            case _:
                raise ValueError(
                    f"Provided mode ({new_mode}) is invalid; "
                    'must either be "two-terminal" or "three-terminal"'
                )
        time.sleep(0.05)

    @property
    def precision_mode(self) -> bool:
        """Specifies whether precision mode is being used."""
        return not ((self.mode_register >> 6) & 1)

    @precision_mode.setter
    def precision_mode(self, state: bool):
        """Sets the state of precision mode; on (True) or off (False)."""
        if state:
            self.write_block_data("mode", self.mode_register & 0b10111111)
        else:
            self.write_block_data("mode", self.mode_register | 0b01000000)
        time.sleep(0.05)
