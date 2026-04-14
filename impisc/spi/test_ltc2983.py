import time
from devices import LTC2983


def main():

    def initalize() -> LTC2983.LTC2983:
        device = LTC2983.LTC2983(0, 0, 20, 21)
        for chan in range(2, 20, 2):
            device.add_rtd_channel(chan, 'PT-500', 20, 100, 'european')  # Temperature reading
        # device.add_rtd_channel(10, 'PT-500', 20, 500, 'european')  # Temperature reading
        device.add_sense_resistor(20, 5100)

        return device

    device = initalize()
    while True:
        for chan in range(2, 20, 2):
            print(f'ch{chan} conversion:', device.read_conversion(chan, force_conversion=True))
        # print('CH10 conversion:', device.read_conversion(10))
        # print('CH20 conversion:', device.read_conversion(20))
        # print('CH18 conversion:', device.read_conversion(18))
        #device._debug_print_channel(2)
        # device._debug_print_channel(10)
        # device._debug_print_channel(20)
        print()
        # time.sleep(0.5)


if __name__ == '__main__':
    main()
