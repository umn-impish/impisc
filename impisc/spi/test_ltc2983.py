from devices import LTC2983


def main():

    def initalize() -> LTC2983.LTC2983:
        device = LTC2983.LTC2983(0, 0, 21, 17)
        device.add_thermocouple_channel(2, 'T', False, 18)
        device.add_rtd_channel(18, 'PT-500', 20, 100, 'european')  # Cold junction compensation
        device.add_rtd_channel(4, 'PT-500', 20, 100, 'european')  # Temperature reading
        device.add_sense_resistor(20, 5100)

        return device

    device = initalize()
    while True:
        device.start_conversion(2)
        device.start_conversion(4)
        print('CH2 conversion:', device.read_conversion(2))
        print('CH4 conversion:', device.read_conversion(4))
        # print('CH18 conversion:', device.read_conversion(18))
        # device._debug_print_channel(2)
        # device._debug_print_channel(4)
        # device._debug_print_channel(18)
        print()


if __name__ == '__main__':
    main()
