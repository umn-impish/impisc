# `quicklooker`
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