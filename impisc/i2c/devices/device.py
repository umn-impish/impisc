"""
Defines a general class to generally interface with I2C devices
along with some useful bit/byte manipulation functions.
"""

from dataclasses import dataclass

import smbus2


def int_to_twos_complement(value: int, bits: int) -> int:
    """Compute the 2's complement of int value.
    From: https://stackoverflow.com/a/9147327
    """
    if (value & (1 << (bits - 1))) != 0:  # if sign bit is set e.g., 8bit: 128-255
        value = value - (1 << bits)  # compute negative value
    return value  # return positive value as is


def twos_complement_to_int(binary_string: str) -> int:
    """Converts a two's complement binary string to an integer."""
    if binary_string[0] == "0":
        return int(binary_string, 2)
    else:
        inverted_string = "".join(["1" if bit == "0" else "0" for bit in binary_string])
        return -(int(inverted_string, 2) + 1)


def _int_to_bytes(value: int, length: int, endianness: str = "big") -> bytearray:
    """Converts the provided integer to a bytearray."""
    try:
        return value.to_bytes(length, endianness)
    except AttributeError:
        output = bytearray()
        for x in range(length):
            offset = x * 8
            mask = 0xFF << offset
            output.append((value & mask) >> offset)
        if endianness == "big":
            output.reverse()
        return output


@dataclass
class Register:
    """Store information regarding a device's register."""

    name: str
    address: int
    num_bits: int


@dataclass
class GenericDevice:
    """Base class for I2C devices."""

    bus_number: int
    address: int

    def __post_init__(self):
        self.registers = {}
        self._bus = smbus2.SMBus(self.bus_number)

    def add_register(self, reg: Register):
        """Add a register to the device."""
        if reg.name in self.registers:
            raise ValueError()
        self.registers[reg.name] = reg

    @property
    def bus(self) -> smbus2.SMBus:
        """The I2C bus needs to be reopened every time since it
        doesn't autoupdate. We close and reopen it so we leave
        unused, open files.
        """
        self._bus.close()
        self._bus = smbus2.SMBus(self.bus_number)

        return self._bus

    @property
    def responsive(self) -> bool:
        """Tries to read data from register 0x00;
        returns boolean indicating success.
        """
        try:
            test_reg = next(iter(self.registers.values()))
            self.read_data(test_reg.address)
            return True
        except Exception as e:  # TODO: specify which Exception
            print(f"Could not ping I2C device at address {hex(self.address)}:\n{e}")
            return False

    def print_register_status(self):
        """Prints the current value for all
        registers associated with the device.
        """
        print("\n------------------------")
        for name in self.registers:
            data = self.read_block_data(name)
            print(f"{name.rjust(10)}:", f"{data:16b}".zfill(16), f"{data}".rjust(8))
        print("------------------------")

    def read_block_data(self, register: str) -> list[int]:
        """Reads all bytes' worth of register data."""
        register = self.registers[register]
        num_bytes = int(register.num_bits // 8)
        value = 0
        for x in self.bus.read_i2c_block_data(
            self.address, register.address, num_bytes
        ):
            value = (value << 8) | x

        return value

    def write_block_data(self, register: str, value: int):
        """Writes all bytes to the register."""
        register = self.registers[register]
        num_bytes = int(register.num_bits // 8)
        bytes_to_send = list(_int_to_bytes(value, num_bytes))
        self.bus.write_i2c_block_data(self.address, register.address, bytes_to_send)

    def read_data(self, register: int) -> int:
        """Reads a single byte from the provided register."""
        return self.bus.read_byte_data(self.address, register)

    def write_data(self, register: int, data: int):
        """Writes a single byte to the provided register."""
        self.bus.write_byte_data(self.address, register, data)
