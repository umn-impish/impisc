import argparse
import os
import sys

from DS3231 import DS3231


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--enable', action='store_true', help='enable PPS')
    parser.add_argument('-d', '--disable', action='store_true', help='disable PPS')
    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='!!! CAUTION !!! force action on DS3231; \
              removes module from Linux Kernel, \
              then adds module to Linux Kernel'
    )
    arg = parser.parse_args()
    enable = arg.enable
    disable = arg.disable
    forced = arg.force

    if not enable and not disable:
        print('Action not specified. Doing nothing.')
        sys.exit(0)
    elif enable and disable:
        print('Ambiguous specification. Doing nothing.')
        sys.exit(0)
    
    if forced:
        print('Removing DS3231 from Linux Kernel')
        os.system('./rtc_disconnect.sh')
    
    address = 0x68 # I2C address
    device = DS3231(1, address)

    if enable:
        device.enable_pps()
        print('PPS enabled')
    elif disable:
        device.disable_pps()
        print('PPS disabled')

    if forced:
        print('Adding DS3231 to Linux Kernel')
        os.system('./rtc_connect.sh')


if __name__ == '__main__':
    main()