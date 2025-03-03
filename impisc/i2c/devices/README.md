# I2C
---
This submodule houses all the I2C definitions and controls.
We opted to write our own code rather than use prexisting device-specific code (i.e. Adafruit) to have the absolute mode control and to make it as clear as possible.

We are using a variety of devices:
- [ADS1015](https://www.ti.com/product/ADS1015) ADC
- [DS3231](https://www.analog.com/en/products/ds3231.html) RTC
- [PCT2075](https://www.nxp.com/products/PCT2075)
