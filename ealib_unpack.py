#!/usr/bin/env python3
"""
Extract files from an Electronic Arts .LIB archive.

Port of the original FreeBASIC LIB extractor.
"""

import argparse
import struct
import sys
from pathlib import Path

import lzss

MAGIC = b"EALIB"

# Each TOC entry: 13-byte null-padded name, 1-byte flags (unused), 4-byte
# little-endian file start offset.
TOC_ENTRY_FORMAT = "<13sBI"
TOC_ENTRY_SIZE = struct.calcsize(TOC_ENTRY_FORMAT)


def read_toc(f, entry_count: int) -> list[tuple[str, int]]:
    """Read the whole table of contents with a single bulk read."""
    raw = f.read(TOC_ENTRY_SIZE * entry_count)
    if len(raw) != TOC_ENTRY_SIZE * entry_count:
        raise EOFError("LIB file is truncated: incomplete table of contents.")

    toc = []
    for name_bytes, flags, start in struct.iter_unpack(TOC_ENTRY_FORMAT, raw):
        name = name_bytes.split(b"\x00", 1)[0].decode("ascii", errors="replace")
        toc.append((name, flags, start))
    return toc


def extract_lib(input_file: str, output_dir: str, *, verbose: bool = True) -> int:
    out_dir = Path(output_dir)

    with open(input_file, "rb") as f:
        magic = f.read(len(MAGIC))
        if magic != MAGIC:
            print("Not an Electronic Arts .LIB file.", file=sys.stderr)
            sys.exit(1)

        # +1 for the sentinel entry that stores the archive's total size.
        entry_count = struct.unpack("<H", f.read(2))[0] + 1

        toc = read_toc(f, entry_count)

        out_dir.mkdir(parents=True, exist_ok=True)

        for (name, flags, start), (_, _, next_start) in zip(toc, toc[1:]):
            if not name or "/" in name or "\\" in name or name in (".", ".."):
                raise ValueError(f"Unsafe or invalid file name in archive: {name!r}")

            file_length = next_start - start
            out_path = out_dir / name

            if verbose:
                print(f"\t{start:08x}\t{flags:08b}\t{out_path}  -  {file_length} bytes")

            f.seek(start)

            if flags & 1:
                header = f.read(4)
                decomp_size = struct.unpack("<I", header)[0]
                data = lzss.decompress(f.read(file_length - 4), 0)
            else:
                data = f.read(file_length)

            out_path.write_bytes(data)

    extracted = entry_count - 1
    if verbose:
        print()
        print(f"{extracted} file(s) extracted.")
    return extracted


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract files from an Electronic Arts .LIB archive."
    )
    parser.add_argument("input_file", help="Path to the EA .LIB file")
    parser.add_argument("output_dir", help="Directory to extract files into")
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress progress output"
    )
    args = parser.parse_args()

    try:
        extract_lib(args.input_file, args.output_dir, verbose=not args.quiet)
    except FileNotFoundError:
        print(f"Error: file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    except (EOFError, ValueError, struct.error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
