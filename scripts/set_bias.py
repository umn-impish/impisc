import argparse

from impisc.i2c.devices.isl22317 import ISL22317


def voltage_to_wiper(voltage: float):
    """Set the wiper to the value closest to the specified voltage."""
    coeffs = [0.0001539627508034794, -0.02828659130768363, 2.0543637222313063, -73.51029051431925, 1106.1317000722063]
    wiper = round(sum(coef * (voltage ** (len(coeffs) - i - 1)) for i, coef in enumerate(coeffs)))
    if wiper not in range(0, 128):
        raise ValueError(f'Wiper must be within [0, 127], not {wiper}. '
                         f'Select a voltage between 28 and 48 V.')
    # print(f'voltage: {voltage}\nwiper: {wiper}')

    return wiper


def set_voltage(voltage: float):
    """Set the bias to the value closest to the specified value."""
    device = ISL22317(0, 0x28)
    device.write_wiper(voltage_to_wiper(voltage))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', type=float, help='desired bias voltage, in volts', required=True)
    arg = parser.parse_args()
    voltage = arg.v
    set_voltage(voltage)


if __name__ == '__main__':
    main()
