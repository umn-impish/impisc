import time

from devices.ads112c04 import ADS112C04


def main():

    device = ADS112C04(1, 0x40)
    device.set_data_rate(20)
    device.enable_turbo_mode()
    device.set_gain(2)
    while True:
        print(f'current mux setting: {device.mux}')
        # print('temperature sensing:', device.temperature_sensing)
        # print('data rate:', device.data_rate)
        reading = device.read_voltage('2', force_conversion=True)
        voltage = reading * (1e6 + 9e3) / 9e3
        print(f'reading: {reading} V')
        # print(f'voltage: {voltage:0.4f}')
        # device.print_register_status()
        temperature = device.read_temperature(force_conversion=False)
        print(f'temperature: {temperature} *C')
        device.power_down()
        time.sleep(5)


if __name__ == '__main__':
    main()
