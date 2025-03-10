import time

from devices.ads1015 import ADS1015


def main():

    device = ADS1015(1, 0x48)
    while True:
        device.set_gain(0.512)
        reading = device.read_voltage(0)
        voltage = reading * (1e6 + 9e3) / 9e3
        print('reading:', reading)
        print('bias:', voltage)
        print()
        time.sleep(0.1)


if __name__ == '__main__':
    main()
