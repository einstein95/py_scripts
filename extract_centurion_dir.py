#!/usr/bin/env python3
# Extract files from .DIR and .DAT files used in the game "Centurion: Defender of Rome" (1990)
# Usage: python3 extract_centurion_dir.py <filename.DIR>

from struct import unpack
from sys import argv

import lzss  # type: ignore

with open(argv[1], "rb") as dir_file, open(
    argv[1].replace(".DIR", ".DAT"), "rb"
) as dat_file:
    while True:
        offset_bytes = dir_file.read(4)
        if not offset_bytes:
            break
        offset = unpack("<I", offset_bytes)[0]
        file_size = unpack("<H", dir_file.read(2))[0]
        file_name = dir_file.read(13).decode().split("\0")[0]
        file_attributes = dir_file.read(1)[0]
        print(f"{offset:08x} {file_size:04x} {file_name} {file_attributes:02x}")
        dat_file.seek(offset)
        file_data = dat_file.read(file_size)
        if file_attributes & 0x80:
            file_data = lzss.decompress(file_data[4:], 0x20202020)
            file_name = file_name.replace(".LZW", ".BIN")
        with open(file_name, "wb") as output_file:
            output_file.write(file_data)
