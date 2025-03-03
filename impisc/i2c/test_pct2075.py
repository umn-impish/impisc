import time

from devices.pct2075 import PCT2075


def main():

    device = PCT2075(1, 0x4f)
    while True:
        print(f'temperature: {device.read_temperature()} *C')
        time.sleep(0.5)


if __name__ == '__main__':
    main()
