#!/usr/bin/env python3
# Extracts files from a PC-8801 tape image in T88 format.
# based on documentation at https://quagma.sakura.ne.jp/manuke/t88format.html
from datetime import timedelta
from io import BufferedWriter
from struct import unpack
from sys import argv
from typing import Optional


def ticks_to_time(ticks):
    total_seconds = ticks / 4800
    td = timedelta(seconds=total_seconds)
    # This gives HH:MM:SS.SSSSSS (6 decimal places)
    hours = int(td.seconds // 3600)
    minutes = (td.seconds // 60) % 60
    seconds = td.seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{td.microseconds:06d}"


with open(argv[1], "rb") as t88_file:
    file_open = False
    file_num = 0
    f: Optional[BufferedWriter] = None
    assert t88_file.read(24) == b"PC-8801 Tape Image(T88)\0"
    while True:
        tag, size = unpack("<HH", t88_file.read(4))
        # print(f"{t88_file.tell() - 4:#x}: Tag {tag} ({size:,} bytes)")
        if tag == 0:  # End tag (終了タグ)
            print(f"End tag @ {t88_file.tell() - 4:#x}")
            remainder = t88_file.read()
            if remainder:
                print(f"Leftover bytes found: {remainder.hex()}")
            t88_file.close()
            break
        if tag == 1:  # Version tag (バージョンタグ)
            ver_min, ver_maj = unpack("<BB", t88_file.read(2))
            print(f"T88 version: {ver_maj}.{ver_min}")
        # These next 3 tags represent areas on the tape that contain no data.
        elif tag == 0x100:  # Blank tag (ブランクタグ)
            # No carrier detected
            start_time, length = unpack("<II", t88_file.read(8))
            print(
                f"{ticks_to_time(start_time)}: Blank tag: {start_time:,} ticks; {length:,} ticks"
            )
        elif tag == 0x102:  # Space tag (スペースタグ)
            # 1200Hz carrier (0) detected
            start_time, length = unpack("<II", t88_file.read(8))
            print(
                f"{ticks_to_time(start_time)}: Space tag: {start_time:,} ticks; {length:,} ticks"
            )
        elif tag == 0x103:  # Mark tag (マークタグ)
            # 2400Hz carrier (1) detected
            start_time, length = unpack("<II", t88_file.read(8))
            print(
                f"{ticks_to_time(start_time)}: Mark tag: {start_time:,} ticks; {length:,} ticks"
            )
        elif tag == 0x101:  # Data tag (データタグ)
            start_time, length, actual_len, actual_type = unpack(
                "<IIHH", t88_file.read(12)
            )
            # length -= 4
            print(
                f"{ticks_to_time(start_time)}: Data tag: {start_time:,} ticks; {length:,} bytes"
            )
            actual_type = {0xCC: "600", 0x1CC: "1200"}.get(
                actual_type, f"Unknown ({actual_type:#x})"
            )
            print(f"  Actual length: {actual_len} bytes")
            print(f"  Baud rate: {actual_type}")
            data = t88_file.read(actual_len)
            # print(data[:0x10].hex())
            has_filename = False
            if data[:0xA] == b"\xd3" * 0xA:  ## BASIC file?
                data = data[0xA:]
                has_filename = True
            elif data[:3] == b"$$$":  # Data file?
                data = data[3:]
                has_filename = True

            if has_filename:
                if f:
                    f.close()
                filename = data.decode("utf-8").rstrip("\x00").rstrip()
                print(f"  Filename: {filename}")
                f = open(filename, "wb")
                file_open = True
            else:
                if not file_open:
                    f = open(f"DATA{file_num}.bin", "wb")
                    file_num += 1
                if not f:
                    raise ValueError("File open for writing but not open, how???")
                f.write(data)
        else:
            print(f"Unknown tag: {tag} @ 0x{t88_file.tell():x}")
