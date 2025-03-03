import time

from devices import ads1015, ds3231, pct2075, manager


REGISTERY = {
    'ADS1015': ads1015.ADS1015(1, 0x48),
    'DS3231': ds3231.DS3231(1, 0x68),
    'PCT2075': pct2075.PCT2075(1, 0x4f)
}


def main():

    man = manager.DeviceManager(REGISTERY)
    while True:
        man.print_status()
        time.sleep(1)


if __name__ == '__main__':
    main()
