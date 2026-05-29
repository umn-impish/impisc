# `impish_monitor`

This module contains code used by the ground station for interfacing with the MariaDB database, used to store the packets sent by IMPISH.
We have one database with four tables corresponding to the various packets defined in `impisc/packets.py`:
- Health
- Quicklook
- Temperatures
- Commands

There are scripts for initializing and resetting the database.
