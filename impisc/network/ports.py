'''
Here are base ports defined for various programs
which will run on IMPISH.

All processes will communicate via UDP sockets.
Each process is assigned a range of 1000 ports to do stuff with.

They are expected to listen to the packet receiver process on
the base port.

For example, the command executor process
shall listen for commands on port 35000.
It may send and receive data on other ports if need be.

It is expected that the listener process will only look at
    port - (port % 1000)
to identify the origin of the data.
'''
import os

# Default to localhost for testing
GRIPS_IP = os.getenv('GRIPS_IP_ADDR') or '127.0.0.1'

GRIPS_EXPOSED = 12345

COMMAND_EXECUTOR = 35000

# XXX update to environment variable which is set
# by the controller installatoin
DETECTOR_CONTROLLER = os.getenv('DET_SERVICE_PORT') or 36000

COMPUTER_MONITOR = 37000
GRIPS_LISTENER = 38000