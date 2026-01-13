"""
Used for creating an executable script that allows one to set the bias
voltage from the command line.
"""

import argparse

from impisc.i2c.devices.isl22317 import ISL22317


def voltage_to_wiper(voltage: float):
    """Set the wiper to the value closest to the specified voltage.
    Currently uses a quartic fit, but we can change this later.
    """
    coeffs = [
        0.0001539627508034794,
        -0.02828659130768363,
        2.0543637222313063,
        -73.51029051431925,
        1106.1317000722063,
    ]
    wiper = round(
        sum(coef * (voltage ** (len(coeffs) - i - 1)) for i, coef in enumerate(coeffs))
    )
    if wiper not in range(0, 128):
        raise ValueError(
            f"Wiper must be within [0, 127], not {wiper}. "
            f"Select a voltage between 28 and 48 V."
        )

    return wiper


def set_voltage(voltage: float):
    """Set the bias to the value closest to the specified value."""
    device = ISL22317(0, 0x28)
    device.awake = True
    device.mode = "two-terminal"
    device.precision_mode = True
    device.wiper = voltage_to_wiper(voltage)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", type=float, help="desired bias voltage, in volts", required=True
    )
    arg = parser.parse_args()
    voltage = arg.v
    set_voltage(voltage)


if __name__ == "__main__":
    main()
