# IMPISC - miscellaneous flight code for IMPISH piggyback
Here are scripts and other helper programs for the IMPISH piggyback.
The main detector code is at [umn-detector-code](https://github.com/umn-impish/umn-detector-code/tree/main),
but we need some supporting code to talk to it and use it effectively.

## Networking system documentation
The current ideation of how packets can get handled is on this
    [Google Slides deck](https://docs.google.com/presentation/d/1wR_YPYLRptlYkl_bsZjN7PZ0DJlXPHNhWncymLepRzg).

## The future
Some things this will (eventually) include:
- helper programs to monitor temperature sensors, voltages, and other health data from components
~~- helper program to wrap/unwrap internal packets using the GRIPS schemes defined in `network`~~
- helper scripts to manage scheduling and ~~abstract command execution~~
- `systemd` files to register programs as services
- probably more
