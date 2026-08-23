#!/usr/bin/env python3
"""
Z3DS Decompressor
Decompresses .z3ds / .zcia / .z3dsx files back to their original ROM format.

Requires the zstandard library:
    pip install zstandard
"""

import argparse
import struct
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import zstandard as zstd
except ImportError:
    sys.exit(
        "Error: 'zstandard' library not found.\n"
        "Install it with:  pip install zstandard"
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAGIC = b"Z3DS"
EXPECTED_VERSION = 0x01

TYPE_END = 0x00
TYPE_BINARY = 0x01

HEADER_FORMAT = "<4s4sBBHIQQ"  # little-endian
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 0x20 = 32 bytes


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Z3DSHeader:
    magic: bytes  # b"Z3DS"
    underlying_magic: bytes  # e.g. b"NCCH"
    version: int
    reserved: int
    header_size: int
    metadata_size: int
    compressed_size: int
    uncompressed_size: int


@dataclass
class MetadataItem:
    name: str
    data: bytes


@dataclass
class Z3DSFile:
    header: Z3DSHeader
    metadata: list[MetadataItem] = field(default_factory=list)
    # compressed payload is read lazily from the file object


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def parse_header(data: bytes) -> Z3DSHeader:
    """Parse the 32-byte Z3DS file header."""
    if len(data) < HEADER_SIZE:
        raise ValueError(
            f"File too small to contain a Z3DS header ({len(data)} bytes)."
        )

    (
        magic,
        underlying_magic,
        version,
        reserved,
        header_size,
        metadata_size,
        compressed_size,
        uncompressed_size,
    ) = struct.unpack_from(HEADER_FORMAT, data, 0)

    if magic != MAGIC:
        raise ValueError(
            f"Bad magic: expected {MAGIC!r}, got {magic!r}. " "Is this a Z3DS file?"
        )
    if version != EXPECTED_VERSION:
        raise ValueError(
            f"Unsupported format version 0x{version:02X}. "
            f"Only version 0x{EXPECTED_VERSION:02X} is supported."
        )

    return Z3DSHeader(
        magic=magic,
        underlying_magic=underlying_magic,
        version=version,
        reserved=reserved,
        header_size=header_size,
        metadata_size=metadata_size,
        compressed_size=compressed_size,
        uncompressed_size=uncompressed_size,
    )


def parse_metadata(data: bytes) -> list[MetadataItem]:
    """
    Parse the optional metadata block.

    Layout:
        [0]    version  u8
        [1…]   items    (repeat until TYPE_END)
        […]    padding  u8[]  (zeros to 16-byte boundary)
    """
    items: list[MetadataItem] = []

    if not data:
        return items

    offset = 0
    meta_version = data[offset]
    offset += 1

    if meta_version != EXPECTED_VERSION:
        print(
            f"  Warning: unknown metadata version 0x{meta_version:02X}; "
            "attempting to parse anyway.",
            file=sys.stderr,
        )

    while offset < len(data):
        if offset + 4 > len(data):
            print("  Warning: truncated item header in metadata.", file=sys.stderr)
            break

        item_type = data[offset]
        name_len = data[offset + 1]
        data_len = struct.unpack_from("<H", data, offset + 2)[0]
        offset += 4

        if item_type == TYPE_END:
            break  # rest is padding

        if item_type != TYPE_BINARY:
            print(
                f"  Warning: unknown item type 0x{item_type:02X} – skipping.",
                file=sys.stderr,
            )
            # still need to advance past name + data
            offset += name_len + data_len
            continue

        if offset + name_len + data_len > len(data):
            print(
                "  Warning: item payload exceeds metadata block – stopping.",
                file=sys.stderr,
            )
            break

        name = data[offset : offset + name_len].decode("utf-8", errors="replace")
        offset += name_len

        payload = data[offset : offset + data_len]
        offset += data_len

        items.append(MetadataItem(name=name, data=payload))

    return items


# ---------------------------------------------------------------------------
# High-level API
# ---------------------------------------------------------------------------


def decompress_z3ds(
    input_path: Path,
    output_path: Path,
    *,
    verbose: bool = False,
) -> None:
    """Decompress a Z3DS file to *output_path*."""

    with input_path.open("rb") as fh:

        # --- Header ---
        raw_header = fh.read(HEADER_SIZE)
        header = parse_header(raw_header)

        # If the writer used a larger header (forward-compat), skip to end.
        if header.header_size > HEADER_SIZE:
            fh.seek(header.header_size)

        if verbose:
            print(f"  Underlying format : {header.underlying_magic.rstrip(b'\\x00')!r}")
            print(f"  Header size       : {header.header_size} bytes")
            print(f"  Metadata size     : {header.metadata_size} bytes")
            print(f"  Compressed size   : {header.compressed_size:,} bytes")
            print(f"  Uncompressed size : {header.uncompressed_size:,} bytes")

        # --- Metadata ---
        metadata: list[MetadataItem] = []
        if header.metadata_size > 0:
            raw_meta = fh.read(header.metadata_size)
            metadata = parse_metadata(raw_meta)

            if verbose and metadata:
                print("  Metadata entries:")
                for item in metadata:
                    try:
                        value = item.data.decode("utf-8")
                    except UnicodeDecodeError:
                        value = f"<{len(item.data)} bytes of binary data>"
                    print(f"    {item.name!r}: {value}")

        # --- Verify file position before reading compressed data ---
        expected_offset = header.header_size + header.metadata_size
        actual_offset = fh.tell()
        if actual_offset != expected_offset:
            fh.seek(expected_offset)

        # --- Decompress ---
        dctx = zstd.ZstdDecompressor()

        written = 0
        with output_path.open("wb") as out_fh:
            with dctx.stream_reader(fh, closefd=False) as reader:
                chunk_size = 256 * 1024  # 256 KB read chunks
                while True:
                    chunk = reader.read(chunk_size)
                    if not chunk:
                        break
                    out_fh.write(chunk)
                    written += len(chunk)

        if written != header.uncompressed_size:
            print(
                f"  Warning: wrote {written:,} bytes but header says "
                f"{header.uncompressed_size:,} bytes.",
                file=sys.stderr,
            )
        elif verbose:
            print(f"  Decompressed      : {written:,} bytes  ✓")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_output_path(input_path: Path) -> Path:
    """
    Derive a sensible output filename from the input.

    Z3DS extensions follow the pattern z<original_ext> or z<original_ext>x,
    e.g.:  .zcci -> .cci,  .zcia -> .cia,  .z3dsx -> .3dsx
    We simply strip the leading 'z' from the extension.
    """
    stem = input_path.stem
    suffix = input_path.suffix  # e.g. ".zcci"

    if suffix.startswith(".z"):
        new_suffix = "." + suffix[2:]  # ".zcci" -> ".cci"
    else:
        new_suffix = ".rom"

    return input_path.with_name(stem + new_suffix)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Decompress a Z3DS-compressed 3DS ROM file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python z3ds_decompress.py game.zcci
  python z3ds_decompress.py game.zcia -o game.cia
  python z3ds_decompress.py game.z3dsx --verbose
        """,
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to the Z3DS-compressed file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path (default: derived from input filename).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print header and metadata information.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )

    args = parser.parse_args()

    input_path: Path = args.input.resolve()
    if not input_path.is_file():
        sys.exit(f"Error: '{input_path}' does not exist or is not a file.")

    output_path: Path = (
        args.output.resolve() if args.output else build_output_path(input_path)
    )

    if output_path.exists() and not args.overwrite:
        sys.exit(
            f"Error: '{output_path}' already exists. " "Use --overwrite to replace it."
        )

    print(f"Input  : {input_path}")
    print(f"Output : {output_path}")

    start = datetime.now()
    try:
        decompress_z3ds(input_path, output_path, verbose=args.verbose)
    except (ValueError, zstd.ZstdError) as exc:
        sys.exit(f"Error: {exc}")

    elapsed = (datetime.now() - start).total_seconds()
    print(f"Done in {elapsed:.2f}s.")


if __name__ == "__main__":
    main()
