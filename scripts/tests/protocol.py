import struct

############# science data protocol ###############

header_fmt_base = "!IIIBBB"
header_base_size = struct.calcsize(header_fmt_base)

"""
Header layout:

uint32 transfer_id
uint32 chunk_index
uint32 total_chunks
uint8 dtype_length
uint8 tag_length
uint8 shape_length
dtype_bytes
tag_bytes
shape (uint32 * shape_len)
data array
"""

def header_format(dtype_len, tag_len, shape_len):
    return header_fmt_base + f"{dtype_len}s{tag_len}s" + ("I" * shape_len)