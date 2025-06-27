'''
Defines a class for interfacing with a ISL22317 I2C digital potentiometer.
'''

from .device import GenericDevice, Register


class ISL22317(GenericDevice):
    '''Interface with a connected ISL22317 digital potentiometer.'''

    def __init__(self, bus_number: int, address: int):
        super().__init__(bus_number=bus_number, address=address)
        self.add_register(Register('wiper', 0x00, 8))  # IVR, WR
        self.add_register(Register('mode', 0x01, 8))  # MSR
        self.add_register(Register('control', 0x02, 8))  # ACR

    def read_wiper(self) -> int:
        '''Returns the value stored in the wiper register (0x00).'''
        value = self.read_block_data('wiper')
        return value

    def write_wiper(self, value: int):
        '''Writes the provided value to the wiper register.
        value must be within [0, 127], otherwise a ValueError is raised.
        '''
        if value not in range(0, 128):
            raise ValueError('Wiper outside valid range: [0, 127]')
        self.write_block_data('wiper', value)
