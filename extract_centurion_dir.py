#!/usr/bin/env python3
# Extract files from .DIR and .DAT files used in the game "Centurion: Defender of Rome" (1990)
# Usage: python3 extract_centurion_dir.py <filename.DIR>

import lzss  # type: ignore
from struct import unpack
from sys import argv

with open(argv[1], "rb") as f, open(argv[1].replace(".DIR", ".DAT"), "rb") as f2:
    while True:
        offset = f.read(4)
        if not offset:
            break
        offset_x = unpack("<I", offset)[0]
        size = unpack("<H", f.read(2))[0]
        filename = f.read(13).decode().split("\0")[0]
        attributes = f.read(1)[0]
        print(f"{offset_x:08x} {size:04x} {filename} {attributes:02x}")
        f2.seek(offset_x)
        data = f2.read(size)
        if attributes & 0x80:
            data = lzss.decompress(data[4:], 0x20202020)
            filename = filename.replace(".LZW", ".BIN")
        with open(filename, "wb") as g:
            g.write(data)
