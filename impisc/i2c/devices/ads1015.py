'''
Defines a class allowing primitive control with the ADS1015 analog-to-digital
converter by Texas Instruments.
'''

import time

from .device import GenericDevice, Register


class ADS1015(GenericDevice):
    '''Interface with a connected ADS1015 ADC.'''

    PIN_MASK = 0b0111000000000000
    PIN_MAP = {
        'AIN0': 0b0100000000000000,
        'AIN1': 0b0101000000000000,
        'AIN2': 0b0110000000000000,
        'AIN3': 0b0111000000000000,
    }

    GAIN_MASK = 0b0000111000000000
    GAIN_MAP = {
        6.144: 0b0000000000000000,
        4.096: 0b0000001000000000,
        2.048: 0b0000010000000000,
        1.024: 0b0000011000000000,
        0.512: 0b0000100000000000,
        0.256: 0b0000101000000000
    }

    def __init__(self, bus_number: int, address: int):

        super().__init__(bus_number=bus_number, address=address)
        self.add_register(Register('conv', 0x00, 16))
        self.add_register(Register('config', 0x01, 16))
        self.set_multiplexer(0)
        self.set_gain(4.096)
        self.set_mode(1)

    @property
    def conversion_status(self) -> bool:
        '''True means performing conversion, False means not converting.'''
        return not bool(self.read_block_data('config') >> 15)

    def set_multiplexer(self, which: int | str):
        '''Select which input to read from: which can be 0, 1, 2, or 3.'''
        pin = f'AIN{which}'
        config_value = self.read_block_data('config')
        config_value &= ~self.PIN_MASK
        config_value += self.PIN_MAP[pin]
        self.write_block_data('config', config_value)

    def set_mode(self, val: int):
        '''0 for continuous conversion,
        1 for single-shot (requires manual conversion).
        '''
        config_register = self.read_block_data('config')
        match val:
            case 0:
                self.write_block_data(
                    'config', 0b1111111011111111 & config_register)
            case 1:
                self.write_block_data(
                    'config', 0b0000000100000000 | config_register)

    def set_gain(self, val: int):
        '''Set the ADC gain.
        Acceptable values are: 0.256, 0.512, 1.024, 2.048, 4.096, 6.144.
        '''
        config_register = self.read_block_data('config')
        config_register &= ~self.GAIN_MASK
        config_register += self.GAIN_MAP[val]
        self.write_block_data('config', config_register)
        self.gain = val

    def start_conversion(self):
        '''Forces the device to write the voltage to the register.'''
        self.write_block_data(
            'config', 0b1000000000000000 | self.read_block_data('config'))

    def wait_for_conversion(self, timeout: float = 0.05):
        '''Loops until either the conversion is over or timeout
        (in seconds) is exceeded.
        '''
        start = time.time()
        while self.conversion_status and (time.time() - start < timeout):
            continue

    def read_voltage(self, pin_number: int):
        '''Reads the voltage from the provided pin (0, 1, 2, or 3).
        Raises a ValueError if pin_number is not contained in [0, 3].

        TODO: See if forcing the conversion is necessary.
        The device appeared to perform conversions even when removed;
        need to better understand how it works. Does it perform a
        conversion when the register is read?
        '''
        if pin_number < 0 or pin_number > 3:
            raise ValueError('pin_number must be within [0,3]')

        self.set_multiplexer(pin_number)
        # if update_register:
        #     self.start_conversion()
        #     self.wait_for_conversion()
        value = self.read_block_data('conv')
        volts = value * self.gain / 32767

        return volts
