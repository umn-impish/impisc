# I2C
---
This submodule houses all the I2C definitions and controls.
We opted to write our own code rather than use prexisting device-specific code (i.e. Adafruit) to have the absolute mode control and to make it as clear as possible.

We have a variety of devices programmed:
- [ADS1015](https://www.ti.com/product/ADS1015) ADC
- [ADS112C04](https://www.ti.com/product/ADS112C04) ADC
- [DS3231](https://www.analog.com/en/products/ds3231.html) RTC
- [PCT2075](https://www.nxp.com/products/PCT2075)
- [MAX11617](https://www.analog.com/en/products/max11617.html) ADC
- [ISL22317](https://www.renesas.com/en/products/isl22317) digital potentiometer
