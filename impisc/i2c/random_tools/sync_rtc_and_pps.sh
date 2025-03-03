#!/bin/bash

sudo modprobe rtc_ds1307
sudo hwclock -w
sudo modprobe -r rtc_ds1307