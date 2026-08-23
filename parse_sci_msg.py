#!/usr/bin/env python3
"""
Extract null-terminated message strings from a message resource
(per the v4.321 layout), ignoring the comment section.

Header (10 bytes):
    0  2  version (== 0x10E1)
    2  2  always zero
    4  2  pointer to comment section (offset from start of resource)
    6  2  number of messages (n)
    8  2  number of comments

Each of the n message records is 12 bytes:
    0  1  noun
    1  1  verb
    2  1  condition
    3  1  sequence
    4  1  talker
    5  2  offset to text (from beginning of resource)
    7  1  noun of referenced message
    8  1  verb of referenced message
    9  1  condition of referenced message
   10  2  always zero
"""

import struct
import sys
from collections import namedtuple


def read_cstring(data: bytes, offset: int) -> str:
    """Read a null-terminated string starting at offset."""
    end: int = data.index(0, offset)
    return data[offset:end].decode("latin-1")


def main(path: str) -> None:
    with open(path, "rb") as f:
        f.seek(2)
        data: bytes = f.read()

    version = struct.unpack_from("<H", data)[0]

    if version == 0x10E1:
        _zero, comment_ptr, n_messages, n_comments = struct.unpack_from(
            "<5H", data[2:], 0
        )
        HEADER_SIZE = 10
        RECORD_SIZE = 11
        RECORD_FMT = "<BBBBBHBBBB"
        REC = namedtuple(
            "Record",
            "noun verb cond seq talker text_off ref_noun ref_verb ref_cond _zero",
        )
    else:
        print("Version not supported")
        sys.exit(1)

    for i in range(n_messages):
        rec_off: int = HEADER_SIZE + i * RECORD_SIZE
        record: REC = REC._make(struct.unpack_from(RECORD_FMT, data, rec_off))

        text: str = read_cstring(data, record.text_off)
        print(record.noun, repr(text))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <message_resource_file>", file=sys.stderr)
        sys.exit(1)

    main(sys.argv[1])
