"""
Defines a class for interfacing with a PCT2075 I2C temperature sensor.
"""

from .device import GenericDevice, Register, int_to_twos_complement


class PCT2075(GenericDevice):
    """Interface with a connected PCT2075 temperature sensor.
    TODO: add and configure hysteresis register.
    """

    def __init__(self, bus_number: int, address: int):
        super().__init__(bus_number=bus_number, address=address)
        self.add_register(Register("temp", 0x00, 16))
        self.add_register(Register("conf", 0x01, 8))

    def read_temperature(self) -> float:
        """Read the temperature from the 0x00 register (temp),
        returned in degrees Celsius.
        """
        comp = (
            int_to_twos_complement(
                self.read_block_data("temp"), self.registers["temp"].num_bits
            )
            >> 5
        )
        return comp / 8
