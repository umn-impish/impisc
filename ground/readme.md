# Ground programs for IMPISC
Here's the basic overview of how things will flow:
1. Data from GRIPS arrives in one big stream
2. The stream is captured by a base program which redirects the stream into a few smaller ones:
    - Telemetry packets are forwarded to a udpcapture
    - Telemetry packets are forwarded to other predefined locations if required
    - Command acks are forwarded to a udpcapture
    - Telemetry is forwarded to other predefined locations if required
3. .... guess that's it

## Commanding
We want to send up commands and receive acknowledgements.
There will only be one program that handles commanding.
This simplifies how acks get routed and gives a central spot for operators to interact with.

### Some general thoughts
- The logic and the interface shall be separate.
- The interface at the moment could be a terminal user interface (TUI)
    written in Python using [`blessed`](https://pypi.org/project/blessed/).
- The logic itself will consist of a few different independent commanding states.
- The command acknowledgement "queue" will always be active while this program is active.