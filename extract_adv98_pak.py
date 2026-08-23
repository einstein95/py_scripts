#!/usr/bin/env python3
"""
Extractor for the FILEPACK .PAK archive format.

Archive layout
--------------
  [0x00]  uint16_le  number of entries (including the ..END sentinel)
  [0x02]  FILEPOS[]  file table, one entry per file + sentinel
              each entry is 16 bytes:
                  [0:11]  char[11]  8-char name + 3-char ext (no dot), space/null padded
                  [11]    char      null terminator (always 0x00)
                  [12:16] int32_le  absolute byte offset of the file data in the archive
  [0x02 + n*16]  raw file data, concatenated in table order

The last table entry has name '..END' and its offset equals the end of the last file.
File sizes are derived from consecutive offsets: size[i] = offset[i+1] - offset[i].
"""

import argparse
import os
import struct
import sys

ENTRY_SIZE = 16  # sizeof(FILEPOS)


def parse_filename(raw: bytes) -> str:
    """Convert the packed 8.3 filename back to a dotted name, e.g. 'MAIN\x00\x00\x00OBJ' -> 'MAIN.OBJ'."""
    name = raw[:8].rstrip(b"\x00 ").decode("ascii", errors="replace")
    ext = raw[8:11].rstrip(b"\x00 ").decode("ascii", errors="replace")
    return f"{name}.{ext}" if ext else name


def read_header(data: memoryview) -> list[dict]:
    """
    Parse the archive header and return a list of entry dicts:
        { 'filename': str, 'offset': int, 'size': int }
    The sentinel ..END entry is excluded from the returned list.
    """
    if len(data) < 2:
        raise ValueError("File too small to be a valid PAK archive.")

    num_entries = struct.unpack_from("<H", data, 0)[0]
    expected_header = 2 + num_entries * ENTRY_SIZE

    if len(data) < expected_header:
        raise ValueError(
            f"Truncated header: need {expected_header} bytes, got {len(data)}."
        )

    entries = []
    for i in range(num_entries):
        base = 2 + i * ENTRY_SIZE
        raw_name = bytes(data[base : base + 11])
        offset = struct.unpack_from("<i", data, base + 12)[
            0
        ]  # signed long in original code
        entries.append({"raw_name": raw_name, "offset": offset})

    # Resolve filenames and sizes; last real entry's size comes from the ..END sentinel
    result = []
    for i, entry in enumerate(entries):
        fname = parse_filename(entry["raw_name"])
        if fname.startswith("..END"):
            break  # sentinel – stop here
        next_offset = entries[i + 1]["offset"]
        size = next_offset - entry["offset"]
        result.append(
            {
                "filename": fname,
                "offset": entry["offset"],
                "size": size,
            }
        )

    return result


def extract(pak_path: str, output_dir: str, verbose: bool = True) -> None:
    with open(pak_path, "rb") as f:
        data = memoryview(f.read())

    entries = read_header(data)

    os.makedirs(output_dir, exist_ok=True)

    print(f"Archive : {pak_path}")
    print(f"Entries : {len(entries)}")
    print(f"Output  : {output_dir}")
    print()

    for entry in entries:
        fname = entry["filename"]
        offset = entry["offset"]
        size = entry["size"]

        if size < 0:
            print(f"  SKIP  {fname!s:<20}  (negative size – corrupt entry)")
            continue

        raw = bytes(data[offset : offset + size])
        if len(raw) != size:
            print(
                f"  WARN  {fname!s:<20}  expected {size} bytes, got {len(raw)} (truncated?)"
            )

        out_path = os.path.join(output_dir, fname)
        with open(out_path, "wb") as out_f:
            out_f.write(raw)

        if verbose:
            print(f"  OK    {fname!s:<20}  {size:>8,} bytes  @ 0x{offset:08X}")

    print()
    print("Done.")


def list_contents(pak_path: str) -> None:
    with open(pak_path, "rb") as f:
        data = memoryview(f.read())

    entries = read_header(data)
    print(f"{'#':>4}  {'Filename':<20}  {'Size':>10}  {'Offset'}")
    print("-" * 52)
    for i, e in enumerate(entries, 1):
        print(f"{i:>4}  {e['filename']:<20}  {e['size']:>10,}  0x{e['offset']:08X}")
    print(f"\n{len(entries)} file(s) in archive.")


def main():
    parser = argparse.ArgumentParser(
        description="Extract files from a FILEPACK .PAK archive."
    )
    parser.add_argument("pak_file", help="Path to the .PAK archive")
    parser.add_argument(
        "-o",
        "--output",
        default="extracted",
        help="Output directory (default: ./extracted)",
    )
    parser.add_argument(
        "-l", "--list", action="store_true", help="List contents without extracting"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress per-file output"
    )
    args = parser.parse_args()

    if not os.path.isfile(args.pak_file):
        print(f"Error: '{args.pak_file}' not found.", file=sys.stderr)
        sys.exit(1)

    if args.list:
        list_contents(args.pak_file)
    else:
        extract(args.pak_file, args.output, verbose=not args.quiet)


if __name__ == "__main__":
    main()
