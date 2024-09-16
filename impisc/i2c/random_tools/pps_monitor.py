import argparse
import datetime
import os
import RPi.GPIO as GPIO
import time


def sync():
    print('syncing RTC and PPS')
    os.system('./sync_rtc_and_pps.sh')


def loop_with_log(pin: int, delay: float):
    
    with open('toggle_log.csv', 'a') as logfile:
        state = GPIO.input(pin)
        while True:
            if GPIO.input(pin) != state:
                now = datetime.datetime.now()
                state = GPIO.input(pin)
                logfile.write(f'{now},{state}\n')
                logfile.flush()
                print(f'[{now}] pin {pin} status: {state}')
            time.sleep(delay)


def loop(pin: int, delay: float):

    state = GPIO.input(pin)
    while True:
        if GPIO.input(pin) != state:
            now = datetime.datetime.now()
            state = GPIO.input(pin)
            print(f'[{now}] pin {pin} status: {state}')
        time.sleep(delay)


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--logging', action='store_true', help='specify whether to log states to csv')
    parser.add_argument('--delay', type=float, default=1e-3, help='how long to sleep, in seconds [default: 1e-3]')
    arg = parser.parse_args()
    keep_log = arg.logging
    delay = arg.delay

    pin = 17
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.IN)
    sync()

    if keep_log:
        loop_with_log(pin, delay)
    else:
        loop(pin, delay)


if __name__ == '__main__':
    main()