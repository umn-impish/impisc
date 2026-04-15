from devices import LTC2983


def main():

    def initalize() -> LTC2983.LTC2983:
        device = LTC2983.LTC2983(0, 0, 20, 21)
        for chan in range(2, 20, 2):
            device.add_rtd_channel(chan, 'PT-500', 20, 100, 'european')
        device.add_sense_resistor(20, 5100)

        return device

    device = initalize()
    while True:
        for chan in range(2, 20, 2):
            print(f'ch{chan} conversion:', device.read_conversion(chan, force_conversion=True))
        print()


if __name__ == '__main__':
    main()
