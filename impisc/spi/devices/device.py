from collections.abc import Generator, Iterable
from contextlib import contextmanager
from dataclasses import dataclass, field

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
    bus_num: int
    cs: int
    registers: dict[str, Register] = field(default_factory=dict)
    _bus: spidev.SpiDev = field(init=False, repr=False, default_factory=spidev.SpiDev)

    def add_register(self, register: Register):
        """Add a register to the device."""
        if register.name in self.registers:
            raise ValueError(f'Register "{register.name}" already in device.')
        self.registers[register.name] = register

    @contextmanager
    def bus(self) -> Generator[spidev.SpiDev]:
        """The I2C bus needs to be reopened every time since it
        doesn't autoupdate. We close and reopen it so we leave
        unused, open files.
        """
        _bus = spidev.SpiDev()
        try:
            _bus.open(self.bus_num, self.cs)
            _bus.max_speed_hz = int(5e5)
            _bus.mode = 0
            yield _bus
        finally:
            _bus.close()

    def read(self, register: str):
        """Read data from the specified register.
        Automatically opens the device, reads data,
        then closes the device.
        """
        with self.bus() as bus:
            data = bus.readbytes(self.registers[register].num_bits // 8)
        return data

    def write(self, data: Iterable) -> None:
        """Write the data to the device."""
        with self.bus() as bus:
            bus.writebytes(data)
