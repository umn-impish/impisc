# Ground programs for IMPISC
Here's the basic overview of how things will flow:
1. Data from GRIPS arrives in one big stream
2. The stream is captured by a base program which redirects the stream into a few smaller ones:
    - Telemetry packets are forwarded to a udpcapture
    - Telemetry packets are forwarded to other predefined locations if required
    - Command acks are forwarded to a udpcapture
    - Telemetry is forwarded to other predefined locations if required
3. .... guess that's it


## How to set up command GUI for testing
### Totally local testing
0. Go to `impisc` and install it to your Python installation. I recommend using `uv` and setting up a venv.
1. Go to the `ground` directory
2. Run `python launch_support.py`; this will run all of the worker programs for both **remote and ground** on localhost.
4. Run `python command_gui.py`. This will pop open a window you can use to send commands to your own computer.
3. Go to the `rust/command_executor` directory. Run `cargo build --release` and then `cargo run --release`. This will run the executor program.
5. Start putting commands into the GUI. It will populate replies and ack packets as they come in.

## Commanding
We want to send up commands and receive acknowledgements.
There will only be one program that handles commanding.
This simplifies how acks get routed and gives a central spot for operators to interact with.

### Currently, only the `ArbitraryLinuxCommand` portion of this commander is implemented. We probably want more than that.

### Some general thoughts
- The logic and the interface shall be separate.
- The interface at the moment could be a terminal user interface (TUI)
    written in Python using [`blessed`](https://pypi.org/project/blessed/).
- The logic itself will consist of a few different independent commanding states.
- The command acknowledgement "queue" will always be active while this program is active.