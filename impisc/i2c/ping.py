import smbus
import time


TEST_ADDRESS = 0x68 # DS3231


def main():

    while True:

        bus = smbus.SMBus(1)
        try:
            data = bus.read_byte_data(TEST_ADDRESS, 0)
            print(f'read byte data from {TEST_ADDRESS}: {data}')
        except OSError as e:
            print('OSError!!!!!!!!')
            print(e)
        
        time.sleep(1)


if __name__ == '__main__':
    main()