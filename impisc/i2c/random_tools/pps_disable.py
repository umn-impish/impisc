from DS3231 import DS3231


def main():

    address = 0x68 # I2C address
    device = DS3231(1, address)
    device.disable_pps()
    print('PPS disabled.')


if __name__ == '__main__':
    main()