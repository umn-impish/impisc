"""
Defines a class allowing primitive control with the MAX11617 analog-to-digital
converter by Texas Instruments.
"""

import smbus2

from .device import GenericDevice


class MAX11617(GenericDevice):
    """Interface with a connected MAX11617 ADC."""

    # The reference voltage map is stripped down from the fully available
    # functionality since we do not need access to all features.
    REFERENCE_VOLTAGE_MAP = {
        "vdd": 0b00000000,
        "external": 0b01000000,  # We will never need this, but included anyway
        "internal": 0b01010000,  # Internal reference, always on
    }

    def __init__(self, bus_number: int, address: int):
        """Initialization always resets the device to default values."""
        super().__init__(bus_number=bus_number, address=address)
        # Set attributes to device defaults.
        # We track these as attributes since the register
        # values cannot be read from the device.
        self._reference = "vdd"
        self.external_clock = False
        self.bipolar = False
        self._scan = 0
        self._channel = 0
        self.single_ended = True
        self.reset_config_register()

    @property
    def setup_register(self) -> int:
        """The current status of the setup register."""
        return (
            0b10000000
            + (self.REFERENCE_VOLTAGE_MAP[self.reference])
            + (self.external_clock << 3)
            + (self.bipolar << 2)
            + 2
        )

    @property
    def config_register(self) -> int:
        """The current status of the configuration register."""
        return (self.scan << 5) + (self.channel << 1) + self.single_ended

    @property
    def channel(self) -> int:
        """The currently selected input channel."""
        return self._channel

    @channel.setter
    def channel(self, new_channel: int):
        """Set the desired input channel.
        Must be within [0, 11].
        """
        if new_channel not in range(0, 12):
            raise ValueError(
                f"channel must be within [0, 11], value {new_channel} is invalid"
            )
        self._channel = new_channel
        self._write_config_register()

    @property
    def scan(self) -> int:
        """The current value for the two scan bits."""
        return self._scan

    @scan.setter
    def scan(self, new_scan: int):
        """Set the value of the scan bits: 0, 1, 2, or 3."""
        if new_scan not in range(0, 4):
            raise ValueError(
                f"scan bits must be within [0, 3], value {new_scan} is invalid"
            )
        self._scan = new_scan
        self._write_config_register()

    @property
    def reference(self) -> str:
        """The source of the reference voltage."""
        return self._reference

    @reference.setter
    def reference(self, new_reference: str):
        """Set the source of the reference voltage:
        "vdd", "internal", or "external".
        """
        new_reference = new_reference.lower()
        if new_reference in self.REFERENCE_VOLTAGE_MAP.keys():
            self._reference = new_reference
            self._write_setup_register()
        else:
            raise ValueError(
                f'Desired reference "{new_reference}" invalid;'
                f"must be one of: {self.REFERENCE_VOLTAGE_MAP.keys()}"
            )

    def _write_setup_register(self):
        """Write the setup register to the device based
        on set parameters.
        """
        self.bus.write_byte(self.address, self.setup_register)

    def _write_config_register(self) -> int:
        """Write the configuration register to the device based
        on set parameters. Returns the register value.
        """
        return self.bus.write_byte(self.address, self.config_register)

    def reset_config_register(self):
        """Resets the configuration register to its default."""
        self.bus.write_byte(self.address, 0b10000000)

    def read_conversion(self, which: int, vref: float | None = None) -> float:
        """Read the voltage from the specified channel.
        which must be between [0, 11]. The reference voltage "vref"
        must be specified if not using the device's internal reference.
        """
        if which not in range(0, 12):
            raise ValueError(f"Selected channel must be within [0, 11], not {which}")
        self.channel = which
        read = smbus2.i2c_msg.read(self.address, 2)
        self.bus.i2c_rdwr(read)
        msb, lsb = list(read)
        value = ((msb & 0x0F) << 8) + lsb
        if self.reference == "internal":
            vref = 2.048
        elif vref is None:
            raise ValueError(
                f"Reference voltage is configured to {self.reference}, "
                "but vref was not specified. Please specify the "
                "vref argument."
            )

        return value / (2**12) * vref
