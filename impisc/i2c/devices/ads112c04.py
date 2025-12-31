"""
Defines a class allowing primitive control with the ADS112C04 analog-to-digital
converter by Texas Instruments.
"""

import time
import smbus2

from .device import GenericDevice, Register


class ADS112C04(GenericDevice):
    """Interface with a connected ADS112C04 ADC."""

    # Config 0
    ANALOG_PIN_MASK = 0b11110000
    SINGLE_ENDED_PIN_MAP = {
        "AIN0": 0b10000000,
        "AIN1": 0b10010000,
        "AIN2": 0b10100000,
        "AIN3": 0b10110000,
    }
    DIFFERENTIAL_PIN_MAP = {
        "AIN01": 0b00000000,
        "AIN02": 0b00010000,
        "AIN03": 0b00100000,
        "AIN10": 0b00110000,
    }
    GAIN_MASK = 0b00001110
    GAIN_MAP = {
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
    SPS_MASK = 0b11100000
    SPS_MAP = {
        20: 0b00000000,
        45: 0b00100000,
        90: 0b01000000,
        175: 0b01100000,
        330: 0b10000000,
        600: 0b10100000,
        1000: 0b11000000,
    }

    def __init__(self, bus_number: int, address: int):
        """Initialization always resets the device to default values
        since the RESET command (0x06) is sent to the device.
        """
        super().__init__(bus_number=bus_number, address=address)
        self.add_register(Register("config0", 0x00, 8))
        self.add_register(Register("config1", 0x01, 8))
        self.add_register(Register("config2", 0x02, 8))
        self.add_register(Register("config3", 0x03, 8))
        self.reset_device()
        # We opt to store these variables rather than reading them
        # from the device registers for speed and ease of access.
        # Also minimizes communication with the device.
        self.gain = 1
        self._data_rate = 20
        self.mux = "01"
        self.turbo_enabled = False

    @property
    def data_rate(self) -> int:
        """The device data rate, taking turbo mode into account."""
        return self._data_rate * (1 + self.turbo_enabled)

    @property
    def pga_bypassed(self) -> bool:
        """Reads the value of the PGA_BYPASS bit in config register 0.
        Returns True if the PGA is bypassed (PGA_BYPASS=1).
        """
        return bool(self.read_block_data("config0") & 1)

    @property
    def conversion_ready(self) -> bool:
        """Reads the value of the DRDY bit in config register 2.
        Returns True if a new conversion result is ready.
        """
        return bool((self.read_block_data("config2") >> 7) & 1)

    @property
    def temperature_sensing(self) -> bool:
        """Reads the value of the TS bit in config register 1.
        Returns True if the temperature sensor is active.

        TODO: Consider making this an object attribute
        so we don't constantly ping the device when
        calling read_voltage() or read_temperature().
        """
        return bool(self.read_block_data("config1") & 1)

    def power_down(self):
        """Sends the POWERDOWN command (0x02) to the device."""
        self.bus.write_byte(self.address, 0x02)

    def reset_device(self):
        """Sends the RESET command (0x06) to the device."""
        self.bus.write_byte(self.address, 0x06)

    def start_sync(self):
        """Sends the START/SYNC command (0x08) to the device.
        In single-shot mode, this starts a single conversion and must
        be called every time an update is desired.
        In continous mode, this only needs to be called once.
        """
        self.bus.write_byte(self.address, 0x08)

    def read_block_data(self, register: str) -> int:
        """Returns the value from the provided register.
        Overrides the Device read_block_data method because the ADS112C04
        requires commands to be sent in order to read register data.
        """
        rreg = 0b00100000 | (self.registers[register].address << 2)  # 0010rrXX
        write = smbus2.i2c_msg.write(self.address, [rreg])
        read = smbus2.i2c_msg.read(
            self.address, length=self.registers[register].num_bits // 8
        )
        successful = False
        while not successful:
            try:
                self.bus.i2c_rdwr(write, read)
                successful = True
            except OSError:
                continue

        return list(read)[0]  # TODO: combine if num bytes > 1

    def write_block_data(self, register: str, value: int):
        """Writes value to the specified register.
        Overrides the Device write_block_data method because the ADS112C04
        requires commands to be sent in order to write register data.
        """
        wreg = 0b01000000 | (self.registers[register].address << 2)  # 0100rrXX
        write = smbus2.i2c_msg.write(self.address, buf=[wreg, value])
        self.bus.i2c_rdwr(write)

    def set_multiplexer(self, which: int | str):
        """Select which input, either single-ended or differential.
        0, 1, 2, 3, 01, 02, 03, 10, ...
        Single-ended measurements are referenced to device GND.
        """
        which = f"{which}".replace("AIN", "")
        match len(which):
            case 1:
                pin_map = self.SINGLE_ENDED_PIN_MAP
                self.disable_pga()  # For bookkeeping purposes
            case 2:
                pin_map = self.DIFFERENTIAL_PIN_MAP
        pin = f"AIN{which}"
        config_register = self.read_block_data("config0")
        config_register &= ~self.ANALOG_PIN_MASK
        try:
            config_register += pin_map[pin]
        except KeyError as e:
            raise ValueError(
                f"Invalid multiplexer pin selection: {pin}\nValid selections: "
                f"\nSingle-ended: {list(ADS112C04.SINGLE_ENDED_PIN_MAP.keys())}"
                f"\nDifferential: {list(ADS112C04.DIFFERENTIAL_PIN_MAP.keys())}"
            ) from e
        self.write_block_data("config0", config_register)
        self.mux = which

    def set_mode(self, mode: int):
        """0 for single-shot (requires manual conversion),
        1 for continuous.
        """
        config_register = self.read_block_data("config1")
        match mode:
            case 0:
                self.write_block_data("config1", 0b11110111 & config_register)
            case 1:
                self.write_block_data("config1", 0b00001000 | config_register)

    def set_gain(self, gain: int):
        """Set the ADC gain.
        Valid values are: 1, 2, 4, 8, 16, 32, 64, 128.
        """
        config_register = self.read_block_data("config0")
        config_register &= ~self.GAIN_MASK
        config_register += self.GAIN_MAP[gain]
        self.write_block_data("config0", config_register)
        self.gain = gain

    def set_data_rate(self, rate: int):
        """Set the device data rate, where rate is in samples per second.
        Valid values are: 20, 45, 90, 175, 330, 600, 1000
        """
        config_register = self.read_block_data("config1")
        config_register &= ~self.SPS_MASK
        config_register += self.SPS_MAP[rate]
        self.write_block_data("config1", config_register)
        self._data_rate = rate

    def enable_pga(self):
        """Sets the last bit in config register 0 to 0.
        This has no effect when reading single-ended analog inputs.
        """
        config_register = self.read_block_data("config0") & 0b11111110
        self.write_block_data("config0", config_register)

    def disable_pga(self):
        """Sets the last bit in config register 0 to 1.
        This has no effect when reading single-ended analog inputs.
        """
        config_register = self.read_block_data("config0") | 0b00000001
        self.write_block_data("config0", config_register)

    def enable_temperature_sensor(self):
        """Enables the temperature sensor.
        Sets the TS bit in config register 1 to 1.
        """
        config_register = self.read_block_data("config1") | 0b00000001
        self.write_block_data("config1", config_register)

    def disable_temperature_sensor(self):
        """Disables the temperature sensor.
        Sets the TS bit in config register 1 to 0.
        """
        config_register = self.read_block_data("config1") & 0b11111110
        self.write_block_data("config1", config_register)

    def enable_turbo_mode(self):
        """Enables turbo mode, doubling the sample rate."""
        config_register = self.read_block_data("config1") | 0b00010000
        self.write_block_data("config1", config_register)
        self.turbo_enabled = True

    def disable_turbo_mode(self):
        """Disables turbo mode."""
        config_register = self.read_block_data("config1") & 0b11101111
        self.write_block_data("config1", config_register)
        self.turbo_enabled = False

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
        Returns the conversion result in two's complement format.
        """
        if force_conversion:
            self.start_sync()
            self.wait_for_conversion()
        rdata = smbus2.i2c_msg.write(self.address, buf=[0x10])
        read = smbus2.i2c_msg.read(self.address, length=2)
        self.bus.i2c_rdwr(rdata, read)
        msb, lsb = list(read)

        return (msb << 8) + lsb

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
            self.disable_temperature_sensor()
            force_conversion = True
        if self.mux != f"{pin_number}":  # Only change mux if needed; save cycles
            self.set_multiplexer(pin_number)
        value = self.read_conversion(force_conversion)
        # Twos complement
        value = int.from_bytes(value.to_bytes(2), signed=True)

        # Vref = 2.048
        return value * 2.048 / self.gain / 32768

    def read_temperature(self, force_conversion: bool = False) -> float:
        """Reads the temperature. If temperature sensing is disabled,
        it's enabled and a conversion is forced, regardless of
        force_conversion value. Returns temperature is degrees Celsius.
        """
        if not self.temperature_sensing:
            self.enable_temperature_sensor()
            force_conversion = True
        value = self.read_conversion(force_conversion)
        # Twos complement
        value = int.from_bytes(value.to_bytes(2), signed=True) >> 2

        return value * 0.0312
