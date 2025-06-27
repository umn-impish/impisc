import time

from devices.isl22317 import ISL22317


def main():

    device = ISL22317(1, 0x28)
    while True:
        for wiper in range(0, 128):
            device.write_wiper(wiper)
            time.sleep(0.1)
            val = device.read_wiper()
            print(f'wiper value: {val}, {val:0x}')
            print()
            time.sleep(0.2)


if __name__ == '__main__':
    main()
