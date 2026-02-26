# science and debug data packet sender
import os
import math
import time
import ports
import array
import socket
import struct
import logging
from protocol import header_format

print('LOCAL_SCIENCE_FWD_PORT', os.getenv("LOCAL_SCIENCE_FWD_PORT"))
# send_port = int(os.getenv("LOCAL_SCIENCE_FWD_PORT"))
send_port = ports.science_udp_port
science_capture_addr = ("localhost", send_port)
max_chunk_size = 1200

def infer_shape(data):
    shape = []
    while isinstance(data, list):
        shape.append(len(data))
        data = data[0] if data else []
    return tuple(shape)

def separate_channels(simulated_spectra):
    channels = list(zip(*simulated_spectra))
    return channels

def send_udp_data(data, tag: str="spectra", dtype_code:str = "I"):
    """
    Send spectra, waveforms (science + debug) via UDP using protocol.py
    Ensures:
    - header + data chunks never exceeds maximum packet size of 1200
    Supports:
      spectra:  [ [bins], [bins], ... ]
      waveforms: {1: [ [samples], [samples], ... ],
                  2: [ [samples], [samples], ... ],
                  3: [ [samples], [samples], ... ],
                  4: [ [samples], [samples], ... ],
      }
    if all 4 channels are available
    dtypes:
        'I' = uint32 (spectra)
        'f' = floats (waveform)
    """
    if isinstance(data, dict):
        channel_map = data  
    else:
        spec_separated = separate_channels(data)
        channel_map = {i+1: ch_data for i, ch_data in enumerate(spec_separated)}
        n_bins = len(spec_separated[0][0]) if spec_separated[0] else 1000

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:

        for ch_id, ch_data in channel_map.items():
            print("channel id", ch_id, "length", len(ch_data))

            if not ch_data or all(sum(row) == 0 for row in ch_data):
                ch_data = [[0]*n_bins]

            # payload = [val for sublist in ch_data for val in sublist]
            if ch_data and len(ch_data) > 0:
                num_rows = len(ch_data)
                num_cols = len(ch_data[0]) if ch_data[0] is not None else 0
                shape = (int(num_rows), int(num_cols))
            else:
                shape = (0, 0)

            ch_tag = f"{tag}_ch{ch_id}"

            transfer_id = int(time.time()) & 0xFFFFFFFF
            arr = array.array(dtype_code)
            for sublist in ch_data:
                arr.fromlist(sublist)
            data_bytes = arr.tobytes()

            dtype_bytes = dtype_code.encode('utf-8')
            tag_bytes = ch_tag.encode('utf-8')

            shape_len = len(shape)
            tag_len = len(tag_bytes)
            dtype_len = len(dtype_bytes)

            if dtype_len > 255 or tag_len > 255 or shape_len > 255:
                raise ValueError("dtype, tag, and shape lengths must fit in uint8")

            meta_format = header_format(dtype_len, tag_len, shape_len)
            header_size = struct.calcsize(meta_format)

            if header_size >= max_chunk_size:
                raise ValueError(f"Metadata size {header_size} exceeds max chunk size {max_chunk_size}")

            max_data_per_chunk = max_chunk_size - header_size
            total_chunks = math.ceil(len(data_bytes) / max_data_per_chunk)

            for chunk_idx in range(total_chunks):

                start = chunk_idx * max_data_per_chunk
                end = min(start + max_data_per_chunk, len(data_bytes))
                data_chunks = data_bytes[start:end]

                metadata_header = struct.pack(
                    meta_format, transfer_id, chunk_idx, total_chunks, dtype_len, tag_len, shape_len, dtype_bytes, tag_bytes, *shape
                )

                packet = metadata_header + data_chunks

                assert len(packet) <= max_chunk_size, f"Packet size {len(packet)} exceeds max chunk size {max_chunk_size}"

                try:
                    sock.sendto(packet, science_capture_addr)
                    time.sleep(0.00005)
                except Exception as e:
                    logging.warning(f"UDP send failed on chunk {chunk_idx}/{total_chunks}, transfer id {transfer_id}: {e}")

