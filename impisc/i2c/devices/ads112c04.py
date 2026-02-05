"""
Defines a class allowing primitive control with the ADS112C04 analog-to-digital
converter by Texas Instruments.
"""

import struct
import time

from typing import override

import smbus2

from .device import GenericDevice, Register


class ADS112C04(GenericDevice):
    """Interface with a connected ADS112C04 ADC."""

    # Command bytes
    CMD_POWERDOWN: int = 0x02
    CMD_RESET: int = 0x06
    CMD_START_SYNC: int = 0x08
    CMD_READ_CONVERSION: int = 0x10

    # Config 0
    MUX_MASK: int = 0b11110000
    SINGLE_ENDED_PIN_MAP: dict[str, int] = {
        "AIN0": 0b10000000,
        "AIN1": 0b10010000,
        "AIN2": 0b10100000,
        "AIN3": 0b10110000,
    }
    DIFFERENTIAL_PIN_MAP: dict[str, int] = {
        "AIN01": 0b00000000,
        "AIN02": 0b00010000,
        "AIN03": 0b00100000,
        "AIN10": 0b00110000,
    }
    GAIN_MASK: int = 0b00001110
    GAIN_MAP: dict[int, int] = {
        1: 0b00000000,
        2: 0b00000010,
        4: 0b00000100,
        8: 0b00000110,
        16: 0b00001000,
        32: 0b00001010,
        64: 0b00001100,
        128: 0b00001110,
    }

    # Config 1
    SPS_MASK: int = 0b11100000
    SPS_MAP: dict[int, int] = {
        20: 0b00000000,
        45: 0b00100000,
        90: 0b01000000,
        175: 0b01100000,
        330: 0b10000000,
        600: 0b10100000,
        1000: 0b11000000,
    }

    # Inverted maps (computed once)
    _INV_GAIN_MAP: dict[int, int] = {v: k for k, v in GAIN_MAP.items()}
    _INV_SPS_MAP: dict[int, int] = {v: k for k, v in SPS_MAP.items()}

    def __init__(self, bus_number: int, address: int):
        super().__init__(bus_number=bus_number, address=address)
        self.add_register(Register("config0", 0x00, 8))
        self.add_register(Register("config1", 0x01, 8))
        self.add_register(Register("config2", 0x02, 8))
        self.add_register(Register("config3", 0x03, 8))

    @property
    def mux(self) -> str:
        """The currently selected multiplexer input (analog input)."""
        value: int = self.read_block_data("config0") & self.MUX_MASK
        combined: dict[str, int] = {
            **self.SINGLE_ENDED_PIN_MAP,
            **self.DIFFERENTIAL_PIN_MAP,
        }
        flipped: dict[int, str] = dict((v, k) for k, v in combined.items())
        if value not in flipped:
            raise ValueError(f"Unknown multiplexer value: {value:#010b}")
        return flipped[value].replace("AIN", "")

    @mux.setter
    def mux(self, which: int | str):  # pyright: ignore[reportPropertyTypeMismatch]
        """Select which input, either single-ended or differential.
        0, 1, 2, 3, 01, 02, 03, 10, ...
        Single-ended measurements are referenced to device GND.
        """
        which = f"{which}".replace("AIN", "")
        pin = f"AIN{which}"
        error = ValueError(
            f"Invalid multiplexer pin selection: {pin}\nValid selections: "
            + f"\nSingle-ended: {list(ADS112C04.SINGLE_ENDED_PIN_MAP.keys())}"
            + f"\nDifferential: {list(ADS112C04.DIFFERENTIAL_PIN_MAP.keys())}"
        )
        match len(which):
            case 1:
                pin_map = self.SINGLE_ENDED_PIN_MAP
                # For bookkeeping purposes mark PGA bypass for single-ended
                self.pga_bypassed = True
            case 2:
                pin_map = self.DIFFERENTIAL_PIN_MAP
            case _:
                raise error
        if pin not in pin_map:
            raise error
        config_register = self.read_block_data("config0")
        config_register &= ~self.MUX_MASK
        config_register |= pin_map[pin]
        self.write_block_data("config0", config_register)

    @property
    def gain(self) -> int:
        """The device gain as an integer (1,2,4,...)."""
        masked = self.read_block_data("config0") & self.GAIN_MASK
        if masked not in self._INV_GAIN_MAP:
            raise ValueError(f"Unknown gain bitfield: {masked:#010b}")
        return self._INV_GAIN_MAP[masked]

    @gain.setter
    def gain(self, gain: int):
        """Set the device gain, valid values are:
        1, 2, 4, 8, 16, 32, 64, 128.
        """
        if gain not in self.GAIN_MAP:
            raise ValueError(
                f'Invalid gain selection: "{gain}"\nValid selections: {list(self.GAIN_MAP.keys())}'
            )
        config_register = self.read_block_data("config0")
        config_register &= ~self.GAIN_MASK
        config_register |= self.GAIN_MAP[gain]
        self.write_block_data("config0", config_register)

    @property
    def pga_bypassed(self) -> bool:
        """Reads the value of the PGA_BYPASS bit in config register 0.
        Returns True if the PGA is bypassed (PGA_BYPASS=1).
        """
        return bool(self.read_block_data("config0") & 1)

    @pga_bypassed.setter
    def pga_bypassed(self, bypassed: bool):
        """Specify whether the PGA should be bypassed."""
        if bypassed:
            config_register = self.read_block_data("config0") | 0b00000001
            self.write_block_data("config0", config_register)
        else:
            config_register = self.read_block_data("config0") & 0b11111110
            self.write_block_data("config0", config_register)

    @property
    def data_rate(self) -> int:
        """The device data rate in samples/sec, taking turbo mode into account."""
        return self._data_rate * (1 + int(self.turbo_mode))

    @data_rate.setter
    def data_rate(self, rate: int):
        """Set the device data rate, where rate is in samples per second.
        Valid values are: 20, 45, 90, 175, 330, 600, 1000
        """
        if rate not in self.SPS_MAP:
            raise ValueError(
                f"Invalid data rate: {rate}; valid: {list(self.SPS_MAP.keys())}"
            )
        config_register = self.read_block_data("config1")
        config_register &= ~self.SPS_MASK
        config_register |= self.SPS_MAP[rate]
        self.write_block_data("config1", config_register)

    @property
    def _data_rate(self) -> int:
        """The device data rate (SPS) not accounting for turbo mode."""
        masked = self.read_block_data("config1") & self.SPS_MASK
        if masked not in self._INV_SPS_MAP:
            raise ValueError(f"Unknown SPS bitfield: {masked:#010b}")
        return self._INV_SPS_MAP[masked]

    @property
    def turbo_mode(self) -> bool:
        """Indicates whether turbo mode is enabled."""
        return bool((self.read_block_data("config1") >> 4) & 1)

    @turbo_mode.setter
    def turbo_mode(self, mode: bool):
        """Turn turbo mode on or off."""
        if mode:
            config_register = self.read_block_data("config1") | 0b00010000
            self.write_block_data("config1", config_register)
        else:
            config_register = self.read_block_data("config1") & 0b11101111
            self.write_block_data("config1", config_register)

    @property
    def temperature_sensing(self) -> bool:
        """Specifies whether temperature sensing is enabled."""
        return bool(self.read_block_data("config1") & 1)

    @temperature_sensing.setter
    def temperature_sensing(self, sensing: bool):
        """Enable or disable temperature sensing mode."""
        if sensing:
            config_register = self.read_block_data("config1") | 0b00000001
            self.write_block_data("config1", config_register)
        else:
            config_register = self.read_block_data("config1") & 0b11111110
            self.write_block_data("config1", config_register)

    @property
    def conversion_ready(self) -> bool:
        """Reads the value of the DRDY bit in config register 2.
        Returns True if a new conversion result is ready.
        """
        return bool((self.read_block_data("config2") >> 7) & 1)

    @property
    def continuous_mode(self) -> bool:
        """Specifies whether the device is in continuous mode (True) or single-shot mode."""
        return bool((self.read_block_data("config1") >> 3) & 1)

    @continuous_mode.setter
    def continuous_mode(self, continuous: bool):
        """Set the device in either continuous mode (True) or single-shot (False)."""
        if continuous:
            config_register = self.read_block_data("config1") & 0b11110111
            self.write_block_data("config1", config_register)
            self.start_sync()
        else:
            config_register = self.read_block_data("config1") | 0b00001000
            self.write_block_data("config1", config_register)
            self.start_sync()

    def power_down(self):
        """Sends the POWERDOWN command to the device."""
        self.bus.write_byte(self.address, self.CMD_POWERDOWN)

    def reset(self):
        """Sends the RESET command to the device."""
        self.bus.write_byte(self.address, self.CMD_RESET)

    def start_sync(self):
        """Sends the START/SYNC command to the device.
        In single-shot mode, this starts a single conversion and must
        be called every time an update is desired.
        In continuous mode, this only needs to be called once.
        """
        self.bus.write_byte(self.address, self.CMD_START_SYNC)

    @override
    def read_block_data(self, register: str, timeout: float = 0.01) -> int:
        """Returns the value from the provided register.
        Overrides the Device read_block_data method because the ADS112C04
        requires commands to be sent in order to read register data.
        timeout is the number of seconds it will try to communicate with
        the device in the event of an OSError.
        """
        rreg: int = 0b00100000 | (self.registers[register].address << 2)  # 0010rrXX
        write = smbus2.i2c_msg.write(self.address, [rreg])
        read = smbus2.i2c_msg.read(self.address, self.registers[register].num_bits // 8)
        successful, tries = False, 0
        start = time.time()
        while not successful:
            try:
                self.bus.i2c_rdwr(write, read)
                successful = True
            except OSError as e:
                tries += 1
                if (time.time() - start) > timeout:
                    raise IOError(
                        f"I2C transaction timed out; tried {tries} times"
                    ) from e
                continue

        # read is an i2c_msg, convert to bytes consistently
        return int.from_bytes(bytes(list(read)), byteorder="big", signed=False)

    @override
    def write_block_data(self, register: str, value: int):
        """Writes value to the specified register.
        Overrides the Device write_block_data method because the ADS112C04
        requires commands to be sent in order to write register data.
        """
        wreg: int = 0b01000000 | (self.registers[register].address << 2)  # 0100rrXX
        write = smbus2.i2c_msg.write(self.address, [wreg, value])
        self.bus.i2c_rdwr(write)

    def wait_for_conversion(self, timeout: float = 0.5):
        """Loops until either the conversion is over or timeout
        (in seconds) is exceeded.
        """
        start = time.time()
        while not self.conversion_ready and (time.time() - start < timeout):
            # Don't spam the device; causes I/O error if too short
            time.sleep(1.1 / self.data_rate)

    def read_conversion(self, force_conversion: bool = False) -> int:
        """Reads the most recent conversion result.
        Force a new conversion with force_conversion.
        Returns the conversion result in two's complement format (signed 16-bit).
        """
        if force_conversion:
            self.start_sync()
            self.wait_for_conversion()
        rdata = smbus2.i2c_msg.write(self.address, [self.CMD_READ_CONVERSION])
        read = smbus2.i2c_msg.read(self.address, 2)
        self.bus.i2c_rdwr(rdata, read)

        # Combine and interpret as signed 16-bits big-endian
        return struct.unpack(">h", bytes(list(read)))[0]  # pyright: ignore[reportAny]

    def read_voltage(
        self, pin_number: int | str, force_conversion: bool = False
    ) -> float:
        """Reads the voltage from the provided multiplexer selection,
        chosen with pin_number. See set_multiplexer for options.
        If temperature sensing is enabled, it's disabled and a conversion
        is forced, regardless of force_conversion value.
        Returns voltage on pin_number in volts.
        """
        if self.temperature_sensing:
            self.temperature_sensing = False
            force_conversion = True
        if self.mux != f"{pin_number}":  # Only change mux if needed; save cycles
            self.mux = pin_number
        value = self.read_conversion(force_conversion)

        # Vref = 2.048
        return value * 2.048 / self.gain / 32768

    def read_temperature(self, force_conversion: bool = False) -> float:
        """Reads the temperature. If temperature sensing is disabled,
        it's enabled and a conversion is forced, regardless of
        force_conversion value. Returns temperature in degrees Celsius.
        """
        if not self.temperature_sensing:
            self.temperature_sensing = True
            force_conversion = True
        value = self.read_conversion(force_conversion) >> 2

        return value * 0.0312