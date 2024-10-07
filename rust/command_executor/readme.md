# `command_executor` program
Accepts a Linux command via a UDP packet,
runs it,
and sends the stdout and stderr back in a few packets.

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

