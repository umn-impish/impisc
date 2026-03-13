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


# `command_executor` program
Accepts a Linux command via a UDP packet,
runs it,
and sends the stdout and stderr back in a one or more packets.

The port it listens on by default is 35000.

## Format of command response
- Sections are separated by newlines '\n'
- The total message arrives in chunks of up to 1024 bytes.
- The first line is `ack-ok` if the command executed successfully, else `error`
- The second line is the return code
- The third line is the string literal `stdout`
- The next segment is whatever was on `stdout`
- After the `stdout` segment, the literal `stderr` is printed.
- The next segment is whatever was printed to `stderr`

Once the last packet is sent, the message "finished" is sent,
indicating end of transmission.

## How to build
```bash
cargo build --release
```

## How to run with `cargo`
```bash
cargo run --release
```

## How to install, once you are happy
To install per-user:
```bash
cargo install --path .
```
To install system-wide: IDK google it


# `daqbox-rebinner`
Accepts DAQBOX packets (plus 5B header) and sums them across energy and time
    to form a "quicklook" data product, a la [STIX]().
The original data is 8000B every 32ms; the quicklook is more like 64B every 4s.

## How to build
```bash
cargo build --release
```

## How to run with `cargo`
```bash
cargo run --release
```

## How to install, once you are happy
To install per-user:
```bash
cargo install --path .
```


# `udpcapture`
Captures UDP packets to files, and/or forwards them to other addresses.
Run `udpcapture --help` for more info

## How to build
Make sure you have the Rust dependencies installed.
Then, run
```bash
cargo build --release
```

## How to run with `cargo`
Once you've built the project, you may do
```bash
cargo run --release -- [ program args ]
```
Where the `[ program args ]` are defined by `udpcapture --help`.

## How to install, once you are happy
To install per-user:
```bash
cargo install --path .
```
To install system-wide: IDK google it

## Examples
### UDP capture to a file and forward to two addresses
```bash
udpcapture -p 12345 -b test -l 600 -s 32768 -f 127.0.0.1:61000 -f 127.0.0.1:62000
```

If you want to silence error/debug messages,
    redirect `stderr` to `/dev/null` with `2>/dev/null`.
