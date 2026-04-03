# GPIO edge detector
C program to detect a rising edge on a GPIO pin, using libgpiod version 3

Usage:
```
detect-edge (gpio pin number)
```

Returns 0 upon successful detection,
    1 for timeout (after 2s),
    2 for other error.
Return code is stored in `$?` (bash),
    or accessible from the calling process
    if using e.g. `std::system` in C++.
