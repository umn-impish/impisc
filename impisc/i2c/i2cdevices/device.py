import os
import smbus
import time

from dataclasses import dataclass


@dataclass
class GenericDevice:
    bus_number: int
    address: int
    kernel_driver: str | None = None


    @property
    def bus(self) -> smbus.SMBus:
        """
        The I2C bus needs to be reopened every time since it
        doesn't autoupdate.
        """
        
        return smbus.SMBus(self.bus_number)

    
    @property
    def responsive(self) -> bool:
        """
        Tries to read data from register 0x00;
        returns boolean indicating success.
        """

        try:
            self.read_data(0)
            return True
        except Exception as e:
            print(f'Could not ping I2C device at address {hex(self.address)}:\n{e}')
            return False


    def read_data(self, register: int) -> int:
        """
        Reads data from the provided register.
        """
        
        return self.bus.read_byte_data(self.address, register)


    def write_data(self, register: int, data: int) -> int:
        """
        Writes data from the provided register.
        """
        
        return self.bus.write_byte_data(self.address, register, data)


    def give_to_kernel(self, quiet: bool = True):
        """
        Gives device module to the Linux Kernel.
        TODO: add while loop?
        """

        if self.kernel_driver is not None:
            if not quiet: print(f'Adding {self.kernel_driver} to kernel.')
            os.system(f'sudo modprobe {self.kernel_driver}')
        else:
            if not quiet: print(f'No kernel driver associated with I2C device at address {self.address}')

    
    def release_from_kernel(self, quiet: bool = True):
        """
        Releases device module from the Linux Kernel.
        TODO: add while loop?
        """
        
        if self.kernel_driver is not None:
            if not quiet: print(f'Releasing {self.kernel_driver} from kernel.')
            os.system(f'sudo modprobe -r {self.kernel_driver}')
        else:
            if not quiet: print(f'No kernel driver associated with I2C device at address {self.address}')


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
        """
        The current state of the control register.
        """

        # return self.bus.read_byte_data(self.address, 0x0E)
        return self.read_data(0x0E)


    def enable_pps(self) -> None:
        """
        Enables the PPS.
        """

        mask = 227 # 11100011
        self.write_data(0x0E, self.control_register & mask)
        self._pps_enabled = True


    def disable_pps(self) -> None:
        """
        Disables the PPS.
        """

        mask = 28 # 00011100
        self.write_data(0x0E, self.control_register | mask)
        self._pps_enabled = False


    def toggle_pps(self) -> bool:
        """
        Returns the **new** state of the PPS.
        """

        if self.pps_enabled:
            self.disable_pps()
        else:
            self.enable_pps()

        return self.pps_enabled


    def read_temperature(self) -> float:
        """
        Temperature in degrees celsius.
        """
        
        self._force_convert()
        byte_tmsb = self.read_data(0x11)
        byte_tlsb = self.read_data(0x12)
        tinteger = (byte_tmsb & 0x7f) + ((byte_tmsb & 0x80) >> 7) * -2**8
        tdecimal = (byte_tmsb >> 7) * 2**(-1) + ((byte_tmsb & 0x40) >> 6) * 2**(-2)
        
        return tinteger + tdecimal


    def _force_convert(self) -> bool:
        """
        Force a conversion and wait until it completes.
        This forces an update to the registers storing the temperature.

        Why does this return True?
        """

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


def _test_GenericDevice():
    device = GenericDevice(1, 0x03)


def _test_DS3231():
    
    device = DS3231(1, 0x68)
    device.release_from_kernel()
    print('temperature:', device.read_temperature())
    device.give_to_kernel()
    print('temperature:', device.read_temperature())


if __name__ == '__main__':
    _test_GenericDevice()
    _test_DS3231()