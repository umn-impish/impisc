# relay

NOTE: this is **not** to be installed on the IMPISH flight computer.

This defines some code that simply acts to forward packets from IMPISH to some destination (e.g. the ground station).
Currently, this is installed onto a Raspberry Pi 3 and has a direct ethernet connection to IMPISH.
The intent is to loosely mimic the gondola.
This code will definitely evolve as we receive more details about how the gondola will handle packets.

This will be particularly useful during vacuum testing, as we will be able to place the relay in the chamber with IMPISH and wirelessly forward packets out of the chamber.