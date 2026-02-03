# data packet sender
import socket
import struct
import logging

science_cap_addr = ("127.0.0.1", 13000)
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_udp_data(data_array, tag="spectra"):
    """
    Send a Numpy array via UDP
    Converts to bytes
    """
    data_bytes = data_array.tobytes()

    shape = data_array.shape
    shape_len = len(shape)

    tag_bytes = tag.encode('utf-8')
    tag_len = len(tag_bytes)

    dtype_bytes = data_array.dtype.str.encode('utf-8')
    dtype_len = len(dtype_bytes)

    meta_format = f"!III{dtype_len}s{tag_len}s" + ('I' * shape_len)
    metadata_header = struct.pack(
        meta_format, dtype_len, tag_len, shape_len, dtype_bytes, tag_bytes, *shape
        )

    full_packet = metadata_header + data_bytes
    try:
        udp_sock.sendto(full_packet, science_cap_addr)
    except Exception as e:
        logging.warning(f"UDP send failed: {e}")