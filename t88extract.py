#!/usr/bin/env python3
# Extracts files from a PC-8801 tape image in T88 format.
# based on documentation at https://quagma.sakura.ne.jp/manuke/t88format.html
from struct import unpack
from sys import argv

with open(argv[1], "rb") as t88_file:
    assert t88_file.read(24) == b"PC-8801 Tape Image(T88)\0"
    while True:
        tag, size = unpack("<HH", t88_file.read(4))
        if tag == 0:  # End tag (終了タグ)
            t88_file.close()
            break
        elif tag == 1:  # Version tag (バージョンタグ)
            min, maj = unpack("<BB", t88_file.read(2))
            print(f"T88 version: {maj}.{min}")
        # These next 3 tags represent areas on the tape that contain no data.
        elif tag == 0x100:  # Blank tag (ブランクタグ)
            # No carrier detected
            start_time, length = unpack("<II", t88_file.read(8))
            print(f"Blank tag: {start_time} ticks, {length} ticks")
        elif tag == 0x102:  # Space tag (スペースタグ)
            # 1200Hz carrier (0) detected
            start_time, length = unpack("<II", t88_file.read(8))
            print(f"Space tag: {start_time} ticks, {length} ticks")
        elif tag == 0x103:  # Mark tag (マークタグ)
            # 2400Hz carrier (1) detected
            start_time, length = unpack("<II", t88_file.read(8))
            print(f"Mark tag: {start_time} ticks, {length} ticks")
        elif tag == 0x101:  # Data tag (データタグ)
            start_time, length, actual_len, actual_type = unpack(
                "<IIHH", t88_file.read(12)
            )
            # length -= 4
            data = t88_file.read(actual_len)
            print(f"Data tag: {start_time} ticks, {length} bytes")
            print(f"  Actual length: {actual_len} bytes")
            print(f"  Actual type: {actual_type}")
            if data[:0xA] == b"\xD3" * 0xA:
                filename = data[0xA:].decode("utf-8").rstrip("\x00")
                print(f"  Filename: {filename}")
                f = open(filename, "wb")
            else:
                f.write(data)
        else:
            print(f"Unknown tag: {tag} @ 0x{t88_file.tell():x}")
