import time

from devices.ds3231 import DS3231


def main():

    device = DS3231(1, 0x68)
    device.enable_pps()
    device.release_from_kernel()
    print('temperature:', device.read_temperature())
    device.give_to_kernel()
    print('temperature:', device.read_temperature())


if __name__ == '__main__':
    main()
