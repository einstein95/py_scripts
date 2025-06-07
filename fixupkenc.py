#!/usr/bin/python
from glob import glob
from pathlib import Path
from shutil import move
from sys import argv

# jp = cp932
# eu = cp1252
target_encoding = argv[1]
all_files = [str(file) for file in Path().rglob("*") if file.is_file()]

for current_file in all_files:
    output_filename_bytes = b""
    for char in current_file:
        if ord(char) > 0xDC00:
            output_filename_bytes += bytes([ord(char) - 0xDC00])
        else:
            output_filename_bytes += char.encode("utf8")
    output_filename_bytes = output_filename_bytes.replace(b"/", b"\\")
    new_filename = output_filename_bytes.decode(target_encoding)
    move(current_file, new_filename)
