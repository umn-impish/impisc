import time

from .device import GenericDevice


class DS3231(GenericDevice):
    
    
    def __init__(self, bus_number: int, address: int):
        super().__init__(bus_number=bus_number, address=address, kernel_driver='rtc_ds1307')
        time.sleep(1)
        
        try:
            self.release_from_kernel(quiet=True)
            self.enable_pps() # TODO: Do we want to default the PPS on?
            self.give_to_kernel(quiet=True)
        except OSError as e:
            print(e)
            print('Could not enable PPS. Is DS3231 connected?')
            pass


    @property
    def busy(self) -> bool:
        return (self.read_data(0x0F) & 1 << 2) != 0


    @property
    def pps_enabled(self) -> bool:
        return self._pps_enabled


    @property
    def control_register(self) -> int:
        '''The current state of the control register.'''

        # return self.bus.read_byte_data(self.address, 0x0E)
        return self.read_data(0x0E)


    def enable_pps(self) -> None:
        '''Enables the PPS.'''

        mask = 227 # 11100011
        self.write_data(0x0E, self.control_register & mask)
        self._pps_enabled = True


    def disable_pps(self) -> None:
        '''Disables the PPS.'''

        mask = 28 # 00011100
        self.write_data(0x0E, self.control_register | mask)
        self._pps_enabled = False


    def toggle_pps(self) -> bool:
        '''Returns the **new** state of the PPS.'''

        if self.pps_enabled:
            self.disable_pps()
        else:
            self.enable_pps()

        return self.pps_enabled


    def read_temperature(self) -> float:
        '''Temperature in degrees celsius.'''
        
        self._force_convert()
        byte_tmsb = self.read_data(0x11)
        byte_tlsb = self.read_data(0x12)
        tinteger = (byte_tmsb & 0x7f) + ((byte_tmsb & 0x80) >> 7) * -2**8
        tdecimal = (byte_tmsb >> 7) * 2**(-1) + ((byte_tmsb & 0x40) >> 6) * 2**(-2)
        
        return tinteger + tdecimal


    def _force_convert(self) -> bool:
        '''Force a conversion and wait until it completes.
        This forces an update to the registers storing the temperature.

        Why does this return True?
        '''

        # Wait for an in-progress conversion to complete.
        while self.busy:
            pass

        CONV = 32 # 00100000
        if self.control_register & CONV == 0:
            self.write_data(0x0E, self.control_register | CONV)
        
        while self.control_register & CONV != 0:
            # Wait for the conversion to complete.
            time.sleep(0.1)
            self.read_data(0x0E)
        
        return True


def _test_DS3231():
    
    device = DS3231(1, 0x68)
    device.release_from_kernel()
    print('temperature:', device.read_temperature())
    device.give_to_kernel()
    print('temperature:', device.read_temperature())


if __name__ == '__main__':
    _test_DS3231()