from __future__ import annotations

import ctypes
import os

from collections import OrderedDict
from typing import TYPE_CHECKING

import mysql.connector

from impisc import logging, packets

if TYPE_CHECKING:
    from mysql.connector.pooling import PooledMySQLConnection
    from mysql.connector.abstracts import MySQLConnectionAbstract


DB_NAME = "impish"
HEALTH_TABLE_NAME = "health"
QUICKLOOK_TABLE_NAME = "quicklook"
COMMAND_TABLE_NAME = "commands"
ADDR = ("", 12004)


def validate_packet(full_packet: bytes, ExpectedClass: packets.Packet) -> bool:
    """Check that the packet is the expected type and that its size
    matches what is stated in the header. Returns False if the packet
    is invalid; True if the packet is valid.
    """
    header, packet = packets.split(full_packet)
    if header.id != packets.PACKET_IDS.index(ExpectedClass):
        logging.log_error(
            f"Received unexpected packet (ID {header.id}; SEQ {header.sequence_number}; "
            + f"{ctypes.sizeof(header)} bytes and {ctypes.sizeof(packet) - ctypes.sizeof(header)} bytes)"
            + "; discarding packet"
            + f"{full_packet}"
        )
        return False
    packet_size = ctypes.sizeof(packet)
    if header.packet_size != packet_size:
        logging.log_critical(
            f"Mismatched packet size ({packet_size}) to value"
            + f"in header ({header.packet_size})"
            + "; discarding packet"
            + f"{full_packet}"
        )
        return False
    logging.log_debug(
        f"Header ID: {header.id}  SEQ: {header.sequence_number:>6}  SIZE: {header.packet_size:>5}"
    )
    return True


def process_sequence_number(header: packets.PacketHeader, seq_num: int) -> int:
    """Check that the sequence number in the header is what we expect."""
    if header.sequence_number != seq_num:
        logging.log_warning(
            "Unexpected packet sequence number; received "
            + f"{header.sequence_number}, expected {seq_num}"
        )
        # Realign number
        seq_num = header.sequence_number + 1
    elif seq_num < packets.MAX_SEQUENCE_NUMBER:
        seq_num += 1
    else:
        seq_num = 0

    return seq_num


def connect(
    database: str | None = DB_NAME,
) -> PooledMySQLConnection | MySQLConnectionAbstract:
    """Connect to the impisc_health MySQL database."""
    return mysql.connector.connect(
        host="localhost", user="impish", password=os.environ["PASS"], database=database
    )


def _health_columns() -> OrderedDict[str, str]:
    """The health column names mapped to their data type."""
    fields: list[str] = [f[0] for f in packets.HealthPacket._fields_]
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
            *list((f, "BIT(1)") for f in power_names),
        ]
    )


def _quicklook_columns() -> OrderedDict[str, str]:
    """The quicklook column names mapped to their data type."""
    cols: list[tuple[str, str]] = []
    for c in range(1, packets.NUM_DET_CHANNELS + 1):
        for b in range(1, packets.NUM_QUICKLOOK_BINS + 1):
            cols.append((f"chan{c}_ebin{b}", "INTEGER"))
    return OrderedDict[str, str](
        [("id", "INT AUTO_INCREMENT PRIMARY KEY"), ("unix_timestamp", "INTEGER"), *cols]
    )


HEALTH_COLUMNS: OrderedDict[str, str] = _health_columns()
QUICKLOOK_COLUMNS: OrderedDict[str, str] = _quicklook_columns()
