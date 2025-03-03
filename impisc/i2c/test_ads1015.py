import time

from devices.ads1015 import ADS1015


def main():

    device = ADS1015(1, 0x48)
    while True:
        device.set_gain(4.096)
        voltage = device.read_voltage(0)
        print('voltage:', voltage)
        time.sleep(0.1)


if __name__ == '__main__':
    main()
