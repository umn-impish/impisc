# science and debug data packet sender
import os
import math
import time
import ports
import socket
import struct
import logging
import numpy as np
from protocol import header_format

print('LOCAL_SCIENCE_FWD_PORT', os.getenv("LOCAL_SCIENCE_FWD_PORT"))
send_port = int(os.getenv("LOCAL_SCIENCE_FWD_PORT"))
# send_port = ports.science_udp_port
science_capture_addr = ("localhost", send_port)
max_chunk_size = 1200

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_udp_data(data_array: np.ndarray, tag: str="spectra"):
    """
    Send a Numpy array via UDP using protocol.py
    Ensures:
    - header + data chunks never exceeds maximum packet size of 1200
    """
    if not isinstance(data_array, np.ndarray):
        raise TypeError("data_array must be a numpy.ndarray")

    transfer_id = time.time_ns() & 0xFFFFFFFF

    data_bytes = data_array.tobytes()

    shape = data_array.shape
    dtype_bytes = data_array.dtype.str.encode('utf-8')
    tag_bytes = tag.encode('utf-8')

    shape_len = len(shape)
    tag_len = len(tag_bytes)
    dtype_len = len(dtype_bytes)

    if dtype_len > 255 or tag_len > 255 or shape_len > 255:
        raise ValueError("dtype, tag, and shape lengths must fit in uint8")

    meta_format = header_format(
        dtype_len, tag_len, shape_len
    )

    header_size = struct.calcsize(meta_format)

    if header_size >= max_chunk_size:
        raise ValueError(f"Metadata size {header_size} exceeds max chunk size {max_chunk_size}")

    max_data_per_chunks = max_chunk_size - header_size
    total_chunks = math.ceil(len(data_bytes) / max_data_per_chunks)

    for chunk_idx in range(total_chunks):
        start = chunk_idx * max_data_per_chunks
        end = min(start + max_data_per_chunks, len(data_bytes))
        data_chunks = data_bytes[start:end]

        metadata_header = struct.pack(
            meta_format, transfer_id, chunk_idx, total_chunks, dtype_len, tag_len, shape_len, dtype_bytes, tag_bytes, *shape
        )

        full_packet = metadata_header + data_chunks

        assert len(full_packet) <= max_chunk_size, f"Packet size {len(full_packet)} exceeds max chunk size {max_chunk_size}"

        try:
            sock.sendto(full_packet, science_capture_addr)
            time.sleep(0.00005)
        except Exception as e:
            logging.warning(f"UDP send failed on chunk {chunk_idx}/{total_chunks}, transfer id {transfer_id}: {e}")