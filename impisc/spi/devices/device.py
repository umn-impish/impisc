from dataclasses import dataclass
from typing import Iterable

import spidev


def twos_complement_to_int(binary_string: str) -> int:
    """Converts a two's complement binary string to an integer."""
    if binary_string[0] == "0":
        return int(binary_string, 2)
    else:
        inverted_string = "".join(["1" if bit == "0" else "0" for bit in binary_string])
        return -(int(inverted_string, 2) + 1)


@dataclass
class Register:
    """Store information regarding a device's register."""

    name: str
    address: int
    num_bits: int

    @property
    def num_bytes(self) -> int:
        """Number of bytes in the register."""
        return self.num_bits // 8


@dataclass
class SPIDevice:
    bus: int
    cs: int

    def __post_init__(self):
        self.registers = {}

    def add_register(self, register: Register):
        """Add a register to the device."""
        if register.name in self.registers:
            raise ValueError(f'Register "{register.name}" already in device.')
        self.registers[register.name] = register

    def read(self, register: str):
        """Read data from the specified register.
        Automatically opens the device, reads data,
        then closes the device.
        """
        self._open()
        data = self._spi.readbytes(self.registers[register].num_bits // 8)
        self._close()

        return data

    def write(self, data: Iterable):
        """Write the data to the device."""
        self._open()
        self._spi.writebytes(data)
        self._close()

    def _open(self):
        """Opens SPI port for device."""
        self._spi = spidev.SpiDev()
        self._spi.open(self.bus, self.cs)
        self._spi.max_speed_hz = int(1e5)
        self._spi.mode = 0

    def _close(self):
        """Closes SPI port for device."""
        self._spi.close()
