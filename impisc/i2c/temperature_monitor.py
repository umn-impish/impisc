import datetime
import time

from i2cdevices.device import DS3231


def main():
    
    address = 0x68 # I2C address
    device = DS3231(1, address)
    time.sleep(1.5)
    device.release_from_kernel()

    while True:
        now = datetime.datetime.now()
        print(f'[{now}] DS3231 temperature: {device.read_temperature():0.2f} C')
        time.sleep(1)


if __name__ == '__main__':
    main()