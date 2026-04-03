# IMPISH `systemd` services

Debian uses [`systemd`](https://en.wikipedia.org/wiki/Systemd) by default for managing system organization during and after boot.

Here we define `.service` files which are installed to `/etc/systemd/system` for IMPISH.
Each service should be responsible for a single thing,
    like health packet generation
    or fault handling/monitoring.

`systemd` services can also be used for one-shot tasks.
For example,
    the Pi GPIOs which control voltage outputs need to be initialized to LOW logic level
    after booting,
    so we put that into a `systemd` service as a one-shot task.
