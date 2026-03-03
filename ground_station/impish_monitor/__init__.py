from __future__ import annotations

import os

from collections import OrderedDict
from typing import TYPE_CHECKING

import mysql.connector

from impisc.packets import HealthPacket

# TODO: update this to use definitions within impisc once settled:
NUM_QLOOK_BINS = 4

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
            ("id", "INT AUTO_INCREMENT PRIMARY KEY"),
            ("gs_unix_timestamp", "INTEGER"),
            *list((f, "INTEGER") for f in fields if "extra" not in f),
            *list((f"missing_{f}", "BIT(1)") for f in fields),
            *list((f, "BIT(1)") for f in power_names)
        ]
    )


def _quicklook_columns() -> OrderedDict[str, str]:
    """The quicklook column names mapped to their data type."""
    cols: list[tuple[str, str]] = []
    for c in range(1, 5):
        for b in range(1, NUM_QLOOK_BINS+1):
            cols.append((f"chan{c}_ebin{b}", "INTEGER"))
    return OrderedDict[str, str](
        [
            ("id", "INT AUTO_INCREMENT PRIMARY KEY"),
            ("gs_unix_timestamp", "INTEGER"),
            *cols
        ]
    )


HEALTH_COLUMNS: OrderedDict[str, str] = _health_columns()
QUICKLOOK_COLUMNS: OrderedDict[str, str] = _quicklook_columns()