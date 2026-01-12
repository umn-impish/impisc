"""
Defines a class for interfacing with a PCT2075 I2C temperature sensor.
"""

from .device import GenericDevice, Register, int_to_twos_complement


class PCT2075(GenericDevice):
    """Interface with a connected PCT2075 temperature sensor.
    TODO: add and configure hysteresis register?
    """

    def __init__(self, bus_number: int, address: int):
        super().__init__(bus_number=bus_number, address=address)
        self.add_register(Register("temp", 0x00, 16))
        self.add_register(Register("conf", 0x01, 8))
        self.add_register(Register("tidle", 0x04, 8))

    @property
    def conf_register(self) -> int:
        """The current value in the conf register (0x01)."""
        return self.read_block_data("conf")

    @property
    def is_shutdown(self) -> bool:
        """Indicates whether the device is shutdown (True) or not (False)."""
        return bool(self.conf_register & 1)

    def shutdown(self):
        """Set the device to shutdown mode."""
        self.write_block_data("conf", self.conf_register | 0b00000001)

    def wakeup(self):
        """Wakeup the device from shutdown mode."""
        self.write_block_data("conf", self.conf_register & 0b11111110)

    @property
    def idle_time(self) -> float:
        """The value in the tidle register (0x04), in seconds.
        Valid values range from [0.1, 3.1] seconds, at 0.1 s increments.
        value is rounded to the nearest valid value.
        """
        return (self.read_block_data("tidle") & 0b00011111) / 10

    @idle_time.setter
    def idle_time(self, value: float) -> float:
        """Sets the value in the tidle register (0x04).
        Valid values range from [0.1, 3.1] seconds, at 0.1 s increments.
        value is rounded to the nearest valid value.
        """
        if (value < 0.1) or (value > 3.1):
            raise ValueError(f"Given idle time must be within [0.1, 3.1]; not {value}")
        value = round(value, 1)
        self.write_block_data("tidle", int(value * 10))

    def read_temperature(self) -> float:
        """Read the temperature from the temp register (0x00),
        returned in degrees Celsius.
        """
        comp = (
            int_to_twos_complement(
                self.read_block_data("temp"), self.registers["temp"].num_bits
            )
            >> 5
        )
        return comp / 8
