import os
import smbus2

from dataclasses import dataclass


def _int_to_bytes(value: int, length: int, endianness: str = 'big') -> bytearray:
    '''Converts the provided integer to a bytearray.'''
    
    try:
        return value.to_bytes(length, endianness)
    except AttributeError:
        output = bytearray()
        for x in range(length):
            offset = x * 8
            mask = 0xff << offset
            output.append((value & mask) >> offset)
        if endianness == 'big':
            output.reverse()
        return output


@dataclass
class Register:
    name: str
    address: int
    num_bits: int


@dataclass
class GenericDevice:
    bus_number: int
    address: int
    kernel_driver: str | None = None
    
    def __post_init__(self):
        self.registers = {}

    def add_register(self, reg: Register):
        
        if reg.name in self.registers:
            raise ValueError()
        
        self.registers[reg.name] = reg

    @property
    def bus(self) -> smbus2.SMBus:
        '''The I2C bus needs to be reopened every time since it
        doesn't autoupdate.
        '''
        return smbus2.SMBus(self.bus_number)

    @property
    def responsive(self) -> bool:
        '''Tries to read data from register 0x00;
        returns boolean indicating success.

        TODO: Update this to use an existing register
        '''
        try:
            self.read_data(0x00)
            return True
        except Exception as e:
            print(f'Could not ping I2C device at address {hex(self.address)}:\n{e}')
            return False

    def print_register_status(self):

        print('\n------------')
        for name in self.registers:
            data = self.read_block_data(name)
            print(f'{name.rjust(10)}:', f'{data:16b}'.zfill(16), f'{data}'.rjust(8))
        print('------------')

    def read_block_data(self, register: str) -> list[int]:

        register = self.registers[register]
        num_bytes = register.num_bits // 8
        value = 0
        for x in self.bus.read_i2c_block_data(self.address, register.address, num_bytes):
            value <<= 8
            value |= x

        return value

    def write_block_data(self, register: str, value: int):

        register = self.registers[register]
        num_bytes = register.num_bits // 8
        bytes_to_send = list(_int_to_bytes(value, num_bytes))
        self.bus.write_i2c_block_data(self.address, register.address, bytes_to_send)

    def read_data(self, register: int) -> int:
        '''Reads data from the provided register.'''
        return self.bus.read_byte_data(self.address, register)

    def write_data(self, register: int, data: int) -> int:
        '''Writes data from the provided register.'''
        return self.bus.write_byte_data(self.address, register, data)

    def give_to_kernel(self, quiet: bool = True):
        '''Gives device module to the Linux Kernel.
        TODO: add while loop?
        '''
        if self.kernel_driver is not None:
            if not quiet: print(f'Adding {self.kernel_driver} to kernel.')
            os.system(f'sudo modprobe {self.kernel_driver}')
        else:
            if not quiet: print(f'No kernel driver associated with I2C device at address {self.address}')

    def release_from_kernel(self, quiet: bool = True):
        '''Releases device module from the Linux Kernel.
        TODO: add while loop?
        '''
        if self.kernel_driver is not None:
            if not quiet: print(f'Releasing {self.kernel_driver} from kernel.')
            os.system(f'sudo modprobe -r {self.kernel_driver}')
        else:
            if not quiet: print(f'No kernel driver associated with I2C device at address {self.address}')


def _test_GenericDevice():
    device = GenericDevice(1, 0x03)


if __name__ == '__main__':
    _test_GenericDevice()