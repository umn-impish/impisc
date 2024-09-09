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

## Examples
### UDP capture to a file and forward to two addresses
```bash
udpcapture -p 12345 -b test -l 600 -s 32768 -f 127.0.0.1:61000 -f 127.0.0.1:62000
```