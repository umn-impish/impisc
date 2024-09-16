from DS3231 import DS3231


def main():

    address = 0x68 # I2C address
    device = DS3231(1, address)
    device.enable_pps()
    print('PPS enabled.')


if __name__ == '__main__':
    main()