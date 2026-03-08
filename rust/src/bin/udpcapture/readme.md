# Udpcapture program
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
