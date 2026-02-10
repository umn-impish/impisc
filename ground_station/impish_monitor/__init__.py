from __future__ import annotations

import os

from collections import OrderedDict
from typing import TYPE_CHECKING

import mysql.connector

from impisc.packets import HealthPacket

if TYPE_CHECKING:
    from mysql.connector.pooling import PooledMySQLConnection
    from mysql.connector.abstracts import MySQLConnectionAbstract


DB_NAME = "impish_health"
TABLE_NAME = "health"
ADDR = ("10.42.0.1", 12002)


def connect(
    database: str | None = DB_NAME,
) -> PooledMySQLConnection | MySQLConnectionAbstract:
    """Connect to the impisc_health MySQL database."""
    return mysql.connector.connect(
        host="localhost", user="impish", password=os.environ["PASS"], database=database
    )


def _columns() -> OrderedDict[str, str]:
    """The column names mapped to their data type."""
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
            *list((f"missing_{f}", "INTEGER") for f in fields),
            *list((f, "INTEGER") for f in power_names),
        ]
    )


COLUMNS: OrderedDict[str, str] = _columns()
