import time
from devices.ds3231 import DS3231


# I sometimes get an OSError when first reading the temperature.
# For some reason, the device isn't released from the kernel, even
# though it is supposed to be. Maybe we need a short delay after
# releasing?


def main():

    device = DS3231(1, 0x68)
    time.sleep(1)
    device.release_from_kernel()
    time.sleep(1)
    print('released from kernel')
    print('temperature:', device.read_temperature())
    device.enable_pps()
    print('enabled PPS')
    device.give_to_kernel()
    # device.enable_pps()
    print('given to kernel')
    # Should crash at next line since kernel has control
    try:
        print('temperature:', device.read_temperature())
    except OSError as e:
        print('could not access device since it\'s under '
              'kernel control (this is supposed to happen)')


if __name__ == '__main__':
    main()
