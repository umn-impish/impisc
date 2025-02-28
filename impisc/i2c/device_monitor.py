import datetime
import os
import time

from devices import ads1015, ds3231, manager


REGISTER = {
    'ADS1015': ads1015.ADS1015(1, 0x48),
    'DS3231': ds3231.DS3231(1, 0x68)
}


def main():
    
    man = manager.DeviceManager(REGISTER)
    while True:
        man.print_status()
        # print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        time.sleep(1)
        

if __name__ == '__main__':
    main()