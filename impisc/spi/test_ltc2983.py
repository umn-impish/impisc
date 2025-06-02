from devices import LTC2983


def main():

    def initalize() -> LTC2983.LTC2983:
        device = LTC2983.LTC2983(0, 0, 25, 24)
        device.add_thermocouple_channel(2, 'T', False, 5)
        device.add_cold_junction_channel(5, True, True, True, 3, 1)

        return device

    device = initalize()
    while True:
        # try:
        device.start_conversion(2)
        print('CH2 conversion:', device.read_conversion(2))
        print('CH5 conversion:', device.read_conversion(5))
        device._debug_print_register('command')
        device._debug_print_channel(2)
        device._debug_print_channel(5)
        # time.sleep(0.1)
        # except NotImplementedError as e:
        #     print(e)
        #     time.sleep(1)
        #     device = initalize()


if __name__ == '__main__':
    main()
