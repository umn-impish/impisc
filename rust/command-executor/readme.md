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

