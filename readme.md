# IMPISC - miscellaneous flight code for IMPISH piggyback
Here we'll put scripts and other helper programs for the IMPISH piggyback.
The main detector code is at [umn-detector-code](https://github.com/umn-impish/umn-detector-code/tree/main),
but we need some supporting code to talk to it and use it effectively.

Some things this will (eventually) include:
- helper programs to monitor temperature sensors, voltages, and other health data from components
- helper program to wrap/unwrap internal packets using the GRIPS schemes defined in `network`
- helper scripts to manage scheduling and abstract command execution
- `systemd` files to register programs as services
- probably more
