import datetime
import os
import time

from i2cdevices import device, manager


REGISTER = {
    'DS3231': device.DS3231(1, 0x68)
}


def main():
    
    man = manager.DeviceManager(REGISTER)
    while True:
        man.print_status()
        # print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        time.sleep(1)
        

if __name__ == '__main__':
    main()