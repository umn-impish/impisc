#!/bin/bash

if [ "$1" == "-h" ]; then
  echo "Removes the DS3231 module [rtc_ds1307] from the Linux Kernel"
  exit 0
fi

sudo modprobe -r rtc_ds1307