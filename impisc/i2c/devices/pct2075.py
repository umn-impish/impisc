"""
Defines a class for interfacing with a PCT2075 I2C temperature sensor.
"""

from .device import GenericDevice, Register, int_to_twos_complement


class PCT2075(GenericDevice):
    """Interface with a connected PCT2075 temperature sensor.
    """

    def __init__(self, bus_number: int, address: int):
        super().__init__(bus_number=bus_number, address=address)
        self.add_register(Register("temp", 0x00, 16))
        self.add_register(Register("conf", 0x01, 8))
        self.add_register(Register("thyst", 0x02, 16))
        self.add_register(Register("tos", 0x03, 16))
        self.add_register(Register("tidle", 0x04, 8))

    @property
    def conf_register(self) -> int:
        """The current value in the conf register (0x01)."""
        return self.read_block_data("conf")
    
    @property
    def overtemperature_threshold(self) -> float:
        """The value of the overtemperature shutdown temperature (Tos register; 0x03)."""
        return int_to_twos_complement(self.read_block_data("tos") >> 7, 9) / 2
    
    @overtemperature_threshold.setter
    def overtemperature_threshold(self, value: float):
        """Set the overtemperature threshold; precise to 0.5 deg Celsius.
        Accepted range: [-55, +125] deg Celsius.
        The provided value is rounded to the nearest 0.5 degree.
        """
        value = ((value * 2) // 1) / 2  # Round to nearest 0.5
        if (value < -55) or (value > 125):
            raise ValueError(f"Overtemperature threshold must be within "
                             f"[-55, 125] *C; provided value {value} invalid.")
        value = int.from_bytes((int(value * 2) << 7).to_bytes(2, signed=True))
        self.write_block_data("tos", value)
    
    @property
    def hysteresis_temperature(self) -> float:
        """The value of the overtemperature shutdown temperature (Thyst register; 0x02)."""
        return int_to_twos_complement(self.read_block_data("thyst") >> 7, 9) / 2

    @hysteresis_temperature.setter
    def hysteresis_temperature(self, value: float):
        """Set the hysteresis temperature; precise to 0.5 deg Celsius.
        Accepted range: [-55, +125] deg Celsius.
        The provided value is rounded to the nearest 0.5 degree.
        """
        value = ((value * 2) // 1) / 2  # Round to nearest 0.5
        if (value < -55) or (value > 125):
            raise ValueError(f"Hysteresis temperature must be within "
                             f"[-55, 125] *C; provided value {value} invalid.")
        value = int.from_bytes((int(value * 2) << 7).to_bytes(2, signed=True))
        self.write_block_data("thyst", value)

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
    def os_mode(self) -> str:
        """The current OS (overtemperature shutdown) operation mode.
        Either "comparator" or "interrupt".
        """
        match (self.conf_register >> 1) & 1:
            case 0:
                mode = "comparator"
            case 1:
                mode = "interrupt"

        return mode

    @os_mode.setter
    def os_mode(self, mode: str):
        """Set the OS operation mode to either "comparator" or "interrupt"."""
        match mode:
            case "comparator":
                self.write_block_data("conf", self.conf_register & 0b11111101)
            case "interrupt":
                self.write_block_data("conf", self.conf_register | 0b00000010)
            case _:
                raise ValueError(
                    f"Provided OS mode ({mode}) is invalid; "
                    'must either be "comparator" or "interrupt"'
                )

    @property
    def os_polarity(self) -> str:
        """The current OS (overtemperature shutdown) polarity.
        Either active "low" or "high".
        """
        match (self.conf_register >> 2) & 1:
            case 0:
                polarity = "low"
            case 1:
                polarity = "high"

        return polarity

    @os_polarity.setter
    def os_polarity(self, polarity: str):
        """Set the OS polarity to either "low" or "high"."""
        match polarity:
            case "low":
                self.write_block_data("conf", self.conf_register & 0b11111011)
            case "high":
                self.write_block_data("conf", self.conf_register | 0b00000100)
            case _:
                raise ValueError(
                    f"Provided OS polarity ({polarity}) is invalid; "
                    'must either be "low" or "high"'
                )

    @property
    def os_queue(self) -> int:
        """The current OS (overtemperature shutdown) fault queue value.
        Valid values: 1, 2, 4, 6.
        """
        bits = ((self.read_block_data("conf") >> 3) & 0b11) << 1
        match bits:
            case 0:
                queue = 1
            case x if x in [2, 4, 6]:
                queue = bits

        return queue

    @os_queue.setter
    def os_queue(self, queue: int):
        """Set the OS fault queue to 1, 2, 4, or 6."""
        match queue:
            case 1:
                bits = 0b00
            case x if x in [2, 4, 6]:
                bits = queue << 2
            case _:
                raise ValueError(
                    f"Provided OS fault queue ({queue}) is invalid; "
                    "must be 1, 2, 4, or 6"
                )
        conf_register = self.read_block_data("conf")
        conf_register &= ~0b00011000
        conf_register += bits
        self.write_block_data("conf", conf_register)

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
