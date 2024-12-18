import os

from prettytable import PrettyTable

from .device import GenericDevice, DS3231


class DeviceManager:

    
    def __init__(self, devices: dict[str, GenericDevice]):
        
        self.devices = {}
        for name, device in devices.items():
            self.register_device(name, device)


    def register_device(self, device_name: str, device: GenericDevice):
        self.devices[device_name] = device
        base = ('{color}Registered device '
                f'[{bcolors.OKBLUE}{device_name}'
                '{color}] at address '
                f'[{bcolors.OKBLUE}{hex(device.address)}'
                '{color}] with device manager')
        if device.responsive:
            print(f'{base.format(color=bcolors.OKGREEN)}.{bcolors.ENDC}')
        else:
            print(f'{base.format(color=bcolors.WARNING)}, but it was unresponsive (possibly under kernel control?){bcolors.ENDC}')


    def forget_device(self, device_name: str):
        device = self.devices.pop(device_name)
        print(f'{bcolors.WARNING}Removed device [{device_name}] from device manager.{bcolors.ENDC}')


    def print_status(self):
        # TODO: prettytable has the ability to set a theme. maybe we could use that?

        NAME_COLOR = bcolors.OKBLUE
        ADDRESS_COLOR = bcolors.WARNING
        table = PrettyTable([f'{bcolors.HEADER}STAT{bcolors.ENDC}', f'{NAME_COLOR}NAME{bcolors.ENDC}', f'{ADDRESS_COLOR}ADDR{bcolors.ENDC}'])
        for name, device in self.devices.items():
            if device.responsive:
                color = bcolors.OKGREEN
                response_str = 'OK'
            else:
                color = bcolors.FAIL
                response_str = 'XX'
            row = [f'{color}[{response_str}]{bcolors.ENDC}', f'{NAME_COLOR}{name}{bcolors.ENDC}', f'{ADDRESS_COLOR}{hex(device.address)}{bcolors.ENDC}']
            table.add_row(row)
        
        console_height = os.get_terminal_size().lines
        table_string = table.get_string()
        table_height = table_string.count('\n') + 1
        print('\n' * (console_height-table_height) + table_string)


def _test_DeviceManager():
    manager = DeviceManager({'DS3231': DS3231(1, 0x68)})
    manager.print_status()

    print('\n\n')
    manager = DeviceManager({})
    device = DS3231(1, 0x68)
    manager.register_device('DS3231', device)
    manager.print_status()


# Class for displaying colored text in the console.
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

    def disable(self):
        self.HEADER = ''
        self.OKBLUE = ''
        self.OKGREEN = ''
        self.WARNING = ''
        self.FAIL = ''
        self.ENDC = ''


def _test_bcolors():
    print(f'{bcolors.HEADER} This is the HEADER color')
    print(f'{bcolors.OKBLUE} This is the OKBLUE color')
    print(f'{bcolors.OKGREEN} This is the OKGREEN color')
    print(f'{bcolors.WARNING} This is the WARNING color')
    print(f'{bcolors.FAIL} This is the FAIL color')
    print(f'{bcolors.ENDC} This is the ENDC color')
    print(f'{bcolors.ENDC} This is the ENDC color' + f'{bcolors.FAIL} with the FAIL color')