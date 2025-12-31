import time
from devices.ads1015 import ADS1015
from devices.ads112c04 import ADS112C04
from devices.isl22317 import ISL22317
from devices.ds3231 import DS3231
from devices.pct2075 import PCT2075


def test_ads1015():
    device = ADS1015(1, 0x48)
    for _ in range(100):
        device.set_gain(0.512)
        reading = device.read_voltage(0)
        voltage = reading * (1e6 + 9e3) / 9e3
        print("reading:", reading)
        print("bias:", voltage)
        print()
        time.sleep(0.1)


def test_ads112c04():
    device = ADS112C04(1, 0x40)
    device.set_data_rate(20)
    device.enable_turbo_mode()
    device.set_gain(2)
    for _ in range(3):
        print(f"current mux setting: {device.mux}")
        # print('temperature sensing:', device.temperature_sensing)
        # print('data rate:', device.data_rate)
        reading = device.read_voltage("2", force_conversion=True)
        reading * (1e6 + 9e3) / 9e3
        print(f"reading: {reading} V")
        # print(f'voltage: {voltage:0.4f}')
        # device.print_register_status()
        temperature = device.read_temperature(force_conversion=False)
        print(f"temperature: {temperature} *C")
        device.power_down()
        time.sleep(1)


def test_ds3231():
    # I sometimes get an OSError when first reading the temperature.
    # For some reason, the device isn't released from the kernel, even
    # though it is supposed to be. Maybe we need a short delay after
    # releasing?
    device = DS3231(1, 0x68)
    time.sleep(1)
    device.release_from_kernel()
    time.sleep(1)
    print("released from kernel")
    print("temperature:", device.read_temperature())
    device.enable_pps()
    print("enabled PPS")
    device.give_to_kernel()
    # device.enable_pps()
    print("given to kernel")
    # Should crash at next line since kernel has control
    try:
        print("temperature:", device.read_temperature())
    except OSError:
        print(
            "could not access device since it's under "
            "kernel control (this is supposed to happen)"
        )


def test_isl22317():
    device = ISL22317(1, 0x28)
    while True:
        for wiper in range(0, 128):
            device.write_wiper(wiper)
            time.sleep(0.1)
            val = device.read_wiper()
            print(f"wiper value: {val}, {val:0x}")
            print()
            time.sleep(0.2)


def test_pct2075():
    device = PCT2075(0, 0x4F)
    for _ in range(10):
        print(f"temperature: {device.read_temperature()} *C")
        time.sleep(0.5)


test_pct2075()
