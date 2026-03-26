from __future__ import annotations
"""
Define various helper functions and table columns for our database.
"""

import ctypes
import os
import socket

from collections import OrderedDict
from typing import TYPE_CHECKING, Callable, Never

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


def listener(
    port: int,
    PacketClass: packets.Packet,
    insert_func: Callable[..., None]
) -> Never:
    """Listens for incoming packets."""
    header: packets.PacketHeader
    packet: PacketClass
    logging.log_debug("Opening DB connection")
    db = connect()
    expected_seqnum = 0
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    logging.log_debug(f"Binding to port {port}")
    sock.bind(("", port))
    try:
        while True:
            data, addr = sock.recvfrom(8192)  # pyright: ignore[reportAny]
            logging.log_info(f"{len(data)} bytes received from {addr[0]}:{addr[1]}")
            if validate_packet(full_packet=data, ExpectedClass=PacketClass):
                header, packet = packets.split(data)
                expected_seqnum = process_sequence_number(
                    header,
                    expected_seqnum
                )
                insert_func(db, packet)
            else:
                logging.log_info(
                    "Received unknown or corrupted packet "
                    + f"with {len(data)} bytes\nID: {header.id}\ndata: {data}"
                )
    finally:
        logging.log_debug("Closing DB connection")
        sock.close()
        db.close()


def validate_packet(full_packet: bytes, ExpectedClass: packets.Packet) -> bool:
    """Check that the packet is the expected type and that its size
    matches what is stated in the header. Returns False if the packet
    is invalid; True if the packet is valid.
    """
    header, packet = packets.split(full_packet)
    if header.id != packets.PACKET_IDS.index(ExpectedClass):
        logging.log_error(
            f"Received unexpected packet (ID {header.id}; NUM {header.packet_number}; SEQ {header.sequence_number}; "
            + f"{ctypes.sizeof(header)} bytes and {ctypes.sizeof(packet) - ctypes.sizeof(header)} bytes)"
            + "; discarding packet: "
            + f"{full_packet}"
        )
        return False
    packet_size = ctypes.sizeof(packet)
    if header.packet_size != packet_size:
        logging.log_critical(
            f"Mismatched packet size ({packet_size}) to value "
            + f"in header ({header.packet_size}) "
            + "; discarding packet: "
            + f"{full_packet}"
        )
        return False
    logging.log_debug(
        f"Header ID: {header.id}  NUM: {header.packet_number:>6}  SEQ: {header.sequence_number:>6}  SIZE: {header.packet_size:>5}"
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
    fields.remove("timestamp")
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
            *list((f, "INTEGER") for f in fields if "extra" not in f),
            *list((f"missing_{f}", "BIT(1)") for f in fields),
            ("missing_unix_timestamp", "BIT(1)"),
            *list((f, "BIT(1)") for f in power_names),
        ]
    )


def _quicklook_columns() -> OrderedDict[str, str]:
    """The quicklook column names mapped to their data type."""
    fields: list[str] = [f[0] for f in packets.QuicklookPacket._fields_]
    fields.remove("timestamp")
    fields.remove("channels")
    cols: list[tuple[str, str]] = []
    for c in range(1, packets.NUM_DET_CHANNELS + 1):
        for b in range(1, packets.NUM_QUICKLOOK_BINS + 1):
            cols.append((f"chan{c}_ebin{b}", "INTEGER"))
    return OrderedDict[str, str](
        [
            ("unix_timestamp", "INTEGER PRIMARY KEY"),
            *list((f, "INTEGER") for f in fields),
            *cols,
        ]
    )


def _command_columns() -> OrderedDict[str, str]:
    """The command column names mapped to their data type.
    This one is different from the others since we won't use
    the packet definition from impisc.packets
    """
    return OrderedDict[str, str](
        [
            ("id", "INTEGER UNSIGNED NOT NULL AUTO_INCREMENT UNIQUE KEY"),
            ("hash", "BIGINT UNSIGNED PRIMARY KEY"),
            ("unix_timestamp", "INTEGER UNSIGNED"),
            ("command_counter", "TINYINT UNSIGNED"),
            ("response_sequence", "TINYINT UNSIGNED"),
            ("total_packets_in_response", "TINYINT UNSIGNED"),
            ("cmd", "MEDIUMBLOB"),
            ("status_code", "TINYINT UNSIGNED"),
            ("stdout", "MEDIUMBLOB"),
            ("stderr", "MEDIUMBLOB"),
            ("unparsed", "MEDIUMBLOB"),
        ]
    )


HEALTH_COLUMNS: OrderedDict[str, str] = _health_columns()
QUICKLOOK_COLUMNS: OrderedDict[str, str] = _quicklook_columns()
COMMAND_COLUMNS: OrderedDict[str, str] = _command_columns()
