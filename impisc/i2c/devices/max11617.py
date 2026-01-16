"""
Defines a class allowing primitive control with the MAX11617 analog-to-digital
converter by Texas Instruments.
"""

import struct

from typing import Literal

import smbus2

from .device import GenericDevice


class MAX11617(GenericDevice):
    """Interface with a connected MAX11617 ADC."""

    # The reference voltage map is stripped down from the fully available
    # functionality since we do not need access to all features.
    REFERENCE_VOLTAGE_MAP: dict[str, int] = {
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
        self._reference: Literal["vdd", "external", "internal"] = "vdd"
        self.external_clock: bool = False
        self.bipolar: bool = False
        self._scan: Literal[0, 1, 2, 3] = 0
        self._channel: Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11] = 0
        self.single_ended: bool = True
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
    def channel(self) -> Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]:
        """The currently selected input channel."""
        return self._channel

    @channel.setter
    def channel(self, new_channel: Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]):
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
    def scan(self) -> Literal[0, 1, 2, 3]:
        """The current value for the two scan bits."""
        return self._scan

    @scan.setter
    def scan(self, new_scan: Literal[0, 1, 2, 3]):
        """Set the value of the scan bits."""
        if new_scan not in range(0, 4):
            raise ValueError(
                f"scan bits must be within [0, 3], value {new_scan} is invalid"
            )
        self._scan = new_scan
        self._write_config_register()

    @property
    def reference(self) -> Literal["vdd", "external", "internal"]:
        """The source of the reference voltage."""
        return self._reference

    @reference.setter
    def reference(self, new_reference: Literal["vdd", "external", "internal"]):
        """Set the source of the reference voltage:
        "vdd", "internal", or "external".
        """
        if new_reference in self.REFERENCE_VOLTAGE_MAP.keys():
            self._reference = new_reference
            self._write_setup_register()
        else:
            raise ValueError(
                f'Desired reference "{new_reference}" invalid;'
                + f"must be one of: {self.REFERENCE_VOLTAGE_MAP.keys()}"
            )

    def _write_setup_register(self):
        """Write the setup register to the device based
        on set parameters.
        """
        self.bus.write_byte(self.address, self.setup_register)

    def _write_config_register(self):
        """Write the configuration register to the device based on set parameters."""
        return self.bus.write_byte(self.address, self.config_register)

    def reset_config_register(self):
        """Resets the configuration register to its default."""
        self.bus.write_byte(self.address, 0b10000000)

    def read_conversion(
        self,
        which: Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
        vref: float | None = None,
    ) -> float:
        """Read the voltage from the specified channel.
        which specifies the channel between [0, 11]. The reference voltage "vref"
        must be provided if not using the device's internal reference.
        """
        if which not in range(0, 12):
            raise ValueError(f"Selected channel must be within [0, 11], not {which}")
        if self.reference == "internal":
            vref = 2.048
        elif vref is None:
            raise ValueError(
                f"Reference voltage is configured to {self.reference}, "
                + "but vref was not specified. Please specify the "
                + "vref argument."
            )
        self.channel = which
        read = smbus2.i2c_msg.read(self.address, 2)
        self.bus.i2c_rdwr(read)
        value: int = struct.unpack(">h", bytes(read))[0]  # pyright: ignore[reportAny]
        value &= 0xFFF  # Flip first four bits to zero since they're always high

        return value / (2**12) * vref
