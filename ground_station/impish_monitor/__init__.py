from __future__ import annotations
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


def connect() -> PooledMySQLConnection | MySQLConnectionAbstract:
    """Connect to the impisc_health MySQL database."""
    return mysql.connector.connect(
        host="localhost",
        user="impish",
        password="Supergiant",
        database=DB_NAME
    ) # TODO: remove plain-text password


def _columns() -> OrderedDict[str, str]:
    """The column names mapped to their data type."""
    fields: list[str] = [f[0] for f in HealthPacket._fields_]
    power_names: list[str] = ["power_det1", "power_det2", "power_det3", "power_det4", "power_bias", "power_heater", "power_daqbox"]
    return OrderedDict({
        "id": "INT AUTO_INCREMENT PRIMARY KEY",
        **{f: "INTEGER" for f in fields if "extra" not in f},
        **{f"missing_{f}": "BIT(1)" for f in fields},
        **{f: "BIT(1)" for f in power_names}
    })


COLUMNS: OrderedDict[str, str] = _columns()
