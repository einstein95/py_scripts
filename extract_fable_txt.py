#!/usr/bin/env python3
"""
Unpack the two TOC blocks in a TXT archive.

Usage:
    python unpack_txt.py <file.txt>
"""

import struct
import sys
from pathlib import Path


def unpack_toc(
    f, toc_offset: int, first_entry: int, last_entry: int | None = None
) -> list[bytes]:
    """
    Read a table-of-contents block and return the raw strings.

    Parameters
    ----------
    f : file-like object
        Already opened in binary mode, positioned anywhere.
    toc_offset : int
        Absolute byte offset where the TOC starts.
    first_entry : int
        Index of the first entry to extract (0-based).
    last_entry : int | None
        Index of the last entry to extract (exclusive).
        If None, extract until the end of the TOC.

    Returns
    -------
    list[bytes]
        The strings as raw bytes (no zero-byte, no trailing '$').
    """
    f.seek(toc_offset)
    entry_count = first_entry // 2
    offsets = [struct.unpack("<H", f.read(2))[0] for _ in range(entry_count)]

    if last_entry is None:
        last_entry = entry_count
    else:
        last_entry = min(last_entry, entry_count)

    strings = []
    for idx, offset in enumerate(offsets):
        f.seek(toc_offset + offset)
        end = toc_offset + offsets[idx + 1] if idx + 1 < entry_count else None

        buf = bytearray()
        while end is None or f.tell() < end:
            byte = f.read(1)
            if not byte or byte == b"\0":
                break
            buf.extend(byte)

        # Strip trailing '$' and optional leading control byte
        buf = buf.rstrip(b"$")
        if buf and buf[0] <= 0x0F:
            buf = buf[1:]
        strings.append(bytes(buf))

    return strings


def main(path: Path) -> None:
    with path.open("rb") as f:
        magic = f.read(4)
        if magic != b"TXT\x00":
            print("Not a TXT archive.", file=sys.stderr)
            sys.exit(1)

        toc1_offset, toc2_offset = struct.unpack("<II", f.read(8))

        try:
            first_entry_offset = struct.unpack("<H", f.read(2))[0]
        except struct.error:
            print("No text entries found.", file=sys.stderr)
            sys.exit(0)

        # --- unpack TOC1 ------------------------------------------------------
        strings1 = unpack_toc(f, toc1_offset, first_entry_offset)
        for s in strings1:
            print(s)

        # --- optionally unpack TOC2 ------------------------------------------
        if toc2_offset:
            f.seek(toc2_offset)
            try:
                first_entry_offset = struct.unpack("<H", f.read(2))[0]
            except struct.error:
                print("No text entries found in TOC2.", file=sys.stderr)
                return
            strings2 = unpack_toc(f, toc2_offset, first_entry_offset)
            for s in strings2:
                print(s)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python unpack_txt.py <file.txt>", file=sys.stderr)
        sys.exit(1)
    main(Path(sys.argv[1]))
