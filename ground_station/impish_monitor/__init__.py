from __future__ import annotations

import os

from collections import OrderedDict
from typing import TYPE_CHECKING

import mysql.connector

from impisc.packets import HealthPacket, QuicklookPacket, NUM_DET_CHANNELS, NUM_QUICKLOOK_BINS

if TYPE_CHECKING:
    from mysql.connector.pooling import PooledMySQLConnection
    from mysql.connector.abstracts import MySQLConnectionAbstract


DB_NAME = "impish"
HEALTH_TABLE_NAME = "health"
QUICKLOOK_TABLE_NAME = "quicklook"
ADDR = ("", 12004)


def connect(
    database: str | None = DB_NAME,
) -> PooledMySQLConnection | MySQLConnectionAbstract:
    """Connect to the impisc_health MySQL database."""
    return mysql.connector.connect(
        host="localhost", user="impish", password=os.environ["PASS"], database=database
    )


def _health_columns() -> OrderedDict[str, str]:
    """The health column names mapped to their data type."""
    fields: list[str] = [f[0] for f in HealthPacket._fields_]
    fields.remove("unix_timestamp")
    fields.remove("extra")
    # power_names is for the toggle bits
    power_names: list[str] = [
        "power_det1",
        "power_det2",
        "power_det3",
        "power_det4",
        "power_bias",
        "power_heater",
        "power_daqbox",
    ]
    return OrderedDict[str, str](
        [
            ("unix_timestamp", "INTEGER PRIMARY KEY"),
            ("gs_unix_timestamp", "INTEGER"),
            *list((f, "INTEGER") for f in fields),
            *list((f"missing_{f}", "BIT(1)") for f in fields),
            *list((f, "BIT(1)") for f in power_names),
        ]
    )


def _quicklook_columns() -> OrderedDict[str, str]:
    """The quicklook column names mapped to their data type."""
    fields: list[str] = [f[0] for f in QuicklookPacket._fields_]
    fields.remove("timestamp")
    fields.remove("channels")
    cols: list[tuple[str, str]] = []
    for c in range(1, NUM_DET_CHANNELS + 1):
        for b in range(1, NUM_QUICKLOOK_BINS + 1):
            cols.append((f"chan{c}_ebin{b}", "INTEGER"))
    return OrderedDict[str, str](
        [
            ("unix_timestamp", "INTEGER PRIMARY KEY"),
            *list((f, "INTEGER") for f in fields),
            *cols,
        ]
    )


HEALTH_COLUMNS: OrderedDict[str, str] = _health_columns()
QUICKLOOK_COLUMNS: OrderedDict[str, str] = _quicklook_columns()
