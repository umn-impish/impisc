import struct
import time

from dataclasses import dataclass
from typing import Iterable

from RPi import GPIO

from .device import SPIDevice, Register, twos_complement_to_int

GPIO.setmode(GPIO.BCM)


@dataclass
class LTCRegister(Register):
    '''Store information regarding a register for the LTC2983.'''

    @property
    def address_bytes(self) -> list[int, int]:
        '''Converts the address into a list of 2 bytes.'''
        return list(self.address.to_bytes(2))


@dataclass
class Channel:
    number: int
    sensor_type: str
    config: int

    def __post_init__(self):
        self.config_register = LTCRegister(
            f'CH{self.number}_config', 0x200 + (self.number - 1) * 4, 32)
        self.conversion_register = LTCRegister(
            f'CH{self.number}_conv', 0x010 + (self.number - 1) * 4, 32)

    @property
    def config_address(self) -> int:
        '''Starting address for the channel configuration.'''
        return self.config_register.address

    @property
    def conversion_address(self) -> int:
        '''Starting address for the channel conversion result.'''
        return self.conversion_register.address


class LTC2983(SPIDevice):

    THERMOCOUPLE_TYPE_MAP = {
        'J':   0b00001 << 27,
        'K':   0b00010 << 27,
        'E':   0b00011 << 27,
        'N':   0b00100 << 27,
        'R':   0b00101 << 27,
        'S':   0b00110 << 27,
        'T':   0b00111 << 27,
        'B':   0b01000 << 27}

    def __init__(self, bus: int, cs: int, reset_pin: int, interrupt_pin: int):
        '''Initalizes the device by adding known registers and
        pin connections. The device is reset and then waits until
        the startup sequence is complete.
        '''
        super().__init__(bus, cs)
        self.channels = {}
        self.add_register(LTCRegister('command', 0x000, 8))
        self.add_register(LTCRegister('global_config', 0x0F0, 8))
        self.reset_pin = reset_pin
        self.interrupt_pin = interrupt_pin
        GPIO.setup(reset_pin, GPIO.OUT)
        GPIO.setup(interrupt_pin, GPIO.IN)
        self.reset()
        while not self.startup_complete:
            print('waiting for startup')
            time.sleep(0.1)

    @property
    def startup_complete(self) -> bool:
        '''Check that the startup sequence is complete by checking that
        the command register returns 0x40.
        '''
        return self.read('command')[0] == 0x40

    @property
    def interrupt_status(self) -> bool:
        '''Returns the status of the interrupt pin. High (True) indicates
        the conversion is complete.
        '''
        return bool(GPIO.input(self.interrupt_pin))

    def reset(self):
        '''Reset the device by pulling the RESET pin low.'''
        GPIO.output(self.reset_pin, False)
        time.sleep(0.01)  # Arbitrary sleep time
        GPIO.output(self.reset_pin, True)

    def soft_reset(self):
        '''Reset by reinitalizing the registers.'''
        print('SOFT RESET!!!!!!')
        time.sleep(0.5)
        for number in list(self.channels.keys()):
            channel = Channel(
                number, self.channels[number].sensor_type, self.channels[number].config)
            del self.channels[number]
            del self.registers[channel.config_register.name]
            del self.registers[channel.conversion_register.name]
            self._add_channel(channel)
        # for number, channel in self.channels.items():
        #     self.channels[number] = Channel(
        #         number, channel.sensor_type, channel.config)
        #     self.channels.

    def read(self, register: str) -> Iterable[int]:
        '''Read data from the specified register.'''
        reg = self.registers[register]
        header = [0x03] + reg.address_bytes
        dummy = [0x000] * reg.num_bytes
        # dummy keeps the clock running just long enough
        # so that the device can output the requested data
        self._open()
        data = self._spi.xfer2(header + dummy)
        self._close()

        # Skip first three since they're the READ_BYTE and two address bytes
        return data[3:]

    def write(self, register: str, data: Iterable):
        '''Write data to the specified register.'''
        reg = self.registers[register]
        header = [0x02] + reg.address_bytes
        super().write(header + data)
        """hex_addr = 0
        for i, a in enumerate(reversed(reg.address_bytes)):
            hex_addr += (16**(2*i)) * a
        print('addr:', hex_addr)
        print(
            f'writing data to register {register} {reg.address_bytes} ({hex(hex_addr)}):', data)"""

    def start_conversion(self, channel: int):
        '''Initiates a conversion to the specified channel by writing to
        the command register. channel must be within [1-20].
        if the channel is not registered, an error is raised.
        '''
        if f'CH{channel}_config' not in self.registers:
            raise ValueError(f'Channel \"{channel}\" not configured as '
                             'measurement device.')
        conv = 0b10000000 + channel
        self.write('command', [conv])

    def read_conversion(self, channel: int) -> float:
        '''Read the conversion status for the specified channel.
        Indefinitely waits for the interrupt pin to go high
        if it is low. Returns the temperature.
        '''
        while not self.interrupt_status:
            time.sleep(0.001)
        data = self.read(self.channels[channel].conversion_register.name)
        status = data[0]
        unpacked = struct.unpack('>I', bytes([0] + data[1:]))[0]
        if status != 1:
            print('ERROR!!!!!!!\n\t', f'{data[0]:0b}'.zfill(8))
            # self._interpret_conversion_error(status)
            self.soft_reset()
            # TODO: some default return value here? Otherwise I tihnk it's zero
        temperature = twos_complement_to_int(f'{unpacked:0b}'.zfill(24)) / 1024

        return temperature

    def _interpret_conversion_error(self, status: int):
        raise NotImplementedError('I dumb')

    def _add_channel(self, channel: Channel):
        '''Add a configured channel to the device.
        Automatically configures the corresponding registers.
        '''
        if channel.number in self.channels:
            raise ValueError(f'Channel {channel.number} already in device.')
        self.channels[channel.number] = channel
        self.add_register(channel.config_register)
        self.add_register(channel.conversion_register)
        self.write(
            channel.config_register.name, list(channel.config.to_bytes(4)))

    def add_thermocouple_channel(
        self,
        channel: int,
        thermocouple_type: str,
        single_ended: bool,
        cold_junction_channel: int
    ):
        '''Add a thermocouple-configured channel to the device.

        cold_junction_channel specifies the cold junction channel:
        CH1-20, or 0 for no compensation. If the number is outside
        [0-20], then an error is raised.
        '''
        if thermocouple_type not in self.THERMOCOUPLE_TYPE_MAP:
            raise ValueError('Specified hermocouple type '
                             f'\"{thermocouple_type}\" either '
                             'not supported or invalid.')
        if channel not in range(1, 21):
            raise ValueError('Channel invalid:\ngave: '
                             f'{channel}, must be within [1-20]')
        if channel == 1 and not single_ended:
            raise ValueError('Channel cannot be differential and specified '
                             'to channel 1.')
        if cold_junction_channel not in range(0, 21):
            raise ValueError('Cold junction channel invalid:\ngave: '
                             f'{cold_junction_channel}, must be within [0-20]')
        config = self.THERMOCOUPLE_TYPE_MAP[thermocouple_type]
        config += cold_junction_channel << 22  # cold junction channel
        config += single_ended << 21  # single ended or differential
        config += False << 20  # over-current check
        config += 0 << 18  # over-current value
        data = list(config.to_bytes(4))
        channel = Channel(channel, 'thermocouple', config)
        self._add_channel(channel)
        # self.write(channel.config_register.name, data)

    def add_cold_junction_channel(
        self,
        channel: int,
        single_ended: bool,
        three_readings: bool,
        perform_averaging: bool,
        current_values: int,
        ideality_factor: int
    ):
        '''Add a channel configured for cold junction measurements for
        thermocouple corrections.

        current_values must be 0, 1, 2, or 3

        TODO: implement ideality_factor
        '''
        config = 0b11100 << 27
        config += single_ended << 26
        config += three_readings << 25
        config += perform_averaging << 24
        config += (current_values << 22)
        config += (0b0100000000000000000000)  # TODO: default value for now
        data = list(config.to_bytes(4))
        channel = Channel(channel, 'cold junction', config)
        self._add_channel(channel)
        self.write(channel.config_register.name, data)

    def _debug_print_channel(self, channel: int):
        '''Print all properties of the channel, intended for debug.'''
        def print_data(data: Iterable):
            hex_data = [f'0x{d:03X}' for d in data]
            unpacked = struct.unpack('>I', bytes(data))[0]
            print(f'\tint list: {data}\t\thex list: {hex_data}')
            print(
                f'\tunpacked int: {unpacked:<20}\tunpacked binary: {unpacked:032b}')
        config_raw = self.read(self.channels[channel].config_register.name)
        conv_raw = self.read(self.channels[channel].conversion_register.name)
        print(f'CHANNEL {channel} DEBUG')
        print('='*120)
        print('CONFIG:')
        print_data(config_raw)
        print()
        print('CONVERSION:')
        print_data(conv_raw)
        print('='*120)
        print()

    def _debug_print_register(self, register: str):
        '''Print all properties of the register, intended for debug.'''
        def print_data(data: Iterable):
            hex_data = [f'0x{d:03X}' for d in data]
            unpacked = struct.unpack('>B', bytes(data))[0]
            print(f'\tint list: {data}\t\thex list: {hex_data}')
            print(
                f'\tunpacked int: {unpacked:<20}\tunpacked binary: {unpacked:08b}')
        reg_raw = self.read(register)
        print(f'CHANNEL {register} DEBUG')
        print('='*120)
        print_data(reg_raw)
        print('='*120)
        print()


def ltc_test():
    device = LTC2983(0, 0, reset_pin=25, interrupt_pin=24)
    while True:
        data = device.read('command')
        print('ret:', data)
        device._configure_channel(2, 'T', 5, False)
        print('addr:', hex(device.registers['CH2_config'].address))
        time.sleep(0.4)
        data = device.read('command')
        print('command:', data)
        data = device.read('CH2_config')
        print('CH2_config:', data)
        time.sleep(1)
        for _ in range(0, 10):
            print('initiating conversion')
            device.start_conversion(2)
            time.sleep(1)
            print('CH2 conversion:', device.read_conversion(2))
            # device.start_conversion(3)
            time.sleep(1)
            print('CH5 conversion:', device.read_conversion(5))
            time.sleep(1)
            data = device.read('command')
            print('command:', data)
            # time.sleep(0.002)
            time.sleep(0.1)
        # for i in range(1, 21, 2):
        #     device._configure_channel(i, 'T', i+1, True)
        break


def ltc_test():

    def initalize() -> LTC2983:
        device = LTC2983(0, 0, 25, 24)
        device.add_thermocouple_channel(2, 'T', False, 5)
        device.add_cold_junction_channel(5, True, True, True, 3, 1)

        return device

    device = initalize()
    while True:
        # try:
        device.start_conversion(2)
        print('CH2 conversion:', device.read_conversion(2))
        print('CH5 conversion:', device.read_conversion(5))
        device._debug_print_register('command')
        device._debug_print_channel(2)
        device._debug_print_channel(5)
        # time.sleep(0.1)
        # except NotImplementedError as e:
        #     print(e)
        #     time.sleep(1)
        #     device = initalize()


def main():
    ltc_test()


if __name__ == '__main__':
    main()
