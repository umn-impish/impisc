#!/bin/bash

if [ "$1" == "-h" ]; then
  echo "Adds the DS3231 module [rtc_ds1307] from the Linux Kernel"
  exit 0
fi

sudo modprobe rtc_ds1307