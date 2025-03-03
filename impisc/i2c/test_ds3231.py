import time

from devices.ds3231 import DS3231


def main():

    device = DS3231(1, 0x68)
    device.release_from_kernel()
    print('here')
    print('released from kernel')
    print('temperature:', device.read_temperature())
    device.enable_pps()
    print('enabled PPS')
    device.give_to_kernel()
    # device.enable_pps()
    print('given to kernel')
    print('temperature:', device.read_temperature())


if __name__ == '__main__':
    main()
