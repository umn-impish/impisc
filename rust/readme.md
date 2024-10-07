# Rust programs for IMPISH piggyback
We chose to write some programs in [Rust](https://www.rust-lang.org/)
    for minimal resources,
    reliability, safety, and speed.
These are **core programs**,
    like a Linux command executor,
    and `udpcapture` which handles all of our data.

Compiling them on the [RPi CM4](https://datasheets.raspberrypi.com/cm4/cm4-datasheet.pdf) 
    is not the best idea:
    `rustup` takes a lot of space and is slow to compile on the Pi.
Instead,
    we can cross-compile on a faster computer and
    upload the resulting program to the Pi.
Keeps things simple, as long as we have no
dynamic libraries linked.
Hmm...

## Setup: `rustup`, `cross`, and `podman`
The `rustup` tool allows installation of various
    compilation toolchains and a Rust compiler
    for your system.
On your fast Linux computer,
    this is easy:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Once that's installed, we need the [`cross`](https://github.com/cross-rs/cross) tool.
`cross` lets us compile for other platforms easily--it
    manages annoyances like downloading the correct compiler
    and linker, without much manual intervention.
Kind of amazing if you think about it.
Also dead simple. Just a lot of brains went into making it.
Anyway. . . 

In addition to `cross` you will need a "container engine,"
    either [Docker](https://www.docker.com/) or [podman](https://podman.io/).
I'd say go with podman:
    it's more secure and lighter weight.
Either works.

```bash
# Debian example
sudo apt update
sudo apt install podman
```

## Building a project for the RPi CM4
To build a project using `cross` for the RPi CM4:
```bash
cross build --release --target=aarch64-unknown-linux-gnu
```
