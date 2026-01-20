"""
Defines a general class to generally interface with I2C devices
along with some useful bit/byte manipulation functions.
"""

import os
import syslog

from dataclasses import dataclass, field
from typing import Literal

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


def _int_to_bytes(
    value: int, length: int, endianness: Literal["little", "big"] = "big"
) -> bytearray:
    """Converts the provided integer to a bytearray."""
    try:
        return bytearray(value.to_bytes(length, endianness))
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
    registers: dict[str, Register] = field(default_factory=dict)
    _bus: smbus2.SMBus = field(init=False, repr=False, default_factory=smbus2.SMBus)

    def add_register(self, reg: Register):
        """Add a register to the device."""
        if reg.name in self.registers:
            raise ValueError(
                f"Register {reg.name} already in device register dictionary."
            )
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
        """Pings a device using i2cget; returns boolean indicating success.
        Logged to system journal.
        """
        cmd = f"i2cget -y {self.bus_number} 0x{self.address:02x} >> /dev/null"
        resp: int = os.system(cmd)
        syslog.syslog(syslog.LOG_INFO, f"testing device responsiveness:\n\t{cmd}")

        return resp == 0

    def print_register_status(self):
        """Prints the current value for all
        registers associated with the device.
        """
        print("\n------------------------")
        for name in self.registers:
            data = self.read_block_data(name)
            print(f"{name.rjust(10)}:", f"{data:16b}".zfill(16), f"{data}".rjust(8))
        print("------------------------")

    def read_block_data(self, register: str) -> int:
        """Reads all bytes of register data."""
        reg: Register = self.registers[register]
        num_bytes = int(reg.num_bits // 8)
        value = 0
        for x in self.bus.read_i2c_block_data(self.address, reg.address, num_bytes):
            value = (value << 8) | x

        return value

    def write_block_data(self, register: str, value: int):
        """Writes all bytes to the register."""
        reg: Register = self.registers[register]
        num_bytes = int(reg.num_bits // 8)
        bytes_to_send = list(_int_to_bytes(value, num_bytes))
        self.bus.write_i2c_block_data(self.address, reg.address, bytes_to_send)

    def read_data(self, register: str) -> int:
        """Reads a single byte from the provided register."""
        return self.bus.read_byte_data(self.address, self.registers[register].address)

    def write_data(self, register: str, data: int):
        """Writes a single byte to the provided register."""
        self.bus.write_byte_data(self.address, self.registers[register].address, data)
