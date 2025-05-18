"""
Launch all of the programs that are needed to test the IMPISH networking setup.

This runs both the local and remote programs on the same machine.
"""

import threading
from typing import Callable

# Remote side
from impisc.processes import router, telemeter

# Ground side
import discriminator
import fake_grips
import telemetry_sorter


def spawn_worker(func: Callable[[], None]) -> threading.Thread:
    t = threading.Thread(target=func)
    t.daemon = True
    t.start()
    return t


worker_targets = [
    router.route_data,
    telemeter.telemeter,
    discriminator.discriminate_packets,
    fake_grips.fake_grips,
    telemetry_sorter.sort_telemetry,
]

# Use the main thread for one of the targets
main_func = worker_targets.pop()
workers = [spawn_worker(t) for t in worker_targets]
main_func()
