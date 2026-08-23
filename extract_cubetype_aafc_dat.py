#!/usr/bin/env python3
"""
Decode an XOR-obfuscated AAFC archive and extract its contents, in one
streaming pass (no intermediate decoded copy of the whole file on disk).

The input file is XOR-encoded such that each byte at position `pos`
(0-indexed, from the start of the file) was XOR'd with (pos & 0xff). Since
that key cycles with period 256 and only depends on absolute file position,
decoding can be done on demand: wrap the raw file in a reader that XORs
each byte it returns based on the current offset. That reader is then used
directly to walk the AAFC table of contents AND to stream each entry's
bytes straight to its output path -- so the file is only read once, and
nothing beyond the current chunk is ever held in memory or written to a
scratch file.

AAFC archive format (after decoding):
    - 4-byte magic "AAFC"
    - header padding up to offset 0x10
    - 4-byte big-endian file count
    - a table of contents: `count` entries, back-to-back, each:
        - 4-byte big-endian name length (in UTF-16 code units)
        - name, UTF-16-BE encoded (namelen * 2 bytes)
        - 4-byte big-endian "unknown" field
        - 4-byte big-endian data size
        - if the name ends in "/" and size is 0, it's a directory entry
    - immediately after the full TOC, a single contiguous data section
      holding each non-directory entry's bytes back-to-back, in the same
      order the entries appear in the TOC (NOT interleaved per-entry)

Usage:
    python extract_aafc.py <input_file> <output_folder>
    python extract_aafc.py <input_file> <output_folder> --chunk-size 16777216
"""

import argparse
import sys
from pathlib import Path
from struct import unpack

try:
    import numpy as np

    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False

DEFAULT_CHUNK_SIZE = 16 * 1024 * 1024  # 16 MB
USE_NUMPY = HAVE_NUMPY  # can be disabled via --no-numpy for troubleshooting


class XorReader:
    """
    Wraps a raw binary file object and transparently XOR-decodes bytes as
    they're read, based on absolute position in the file (byte at position
    `pos` was encoded with pos & 0xff). Supports the small subset of
    file-like behavior the AAFC parser needs: read() and seek(offset) from
    the start of the file.
    """

    def __init__(self, path: Path):
        self.f = open(path, "rb")
        self.pos = 0

    def seek(self, offset: int):
        self.f.seek(offset)
        self.pos = offset

    def read(self, n: int) -> bytes:
        raw = self.f.read(n)
        count = len(raw)
        if count == 0:
            return b""

        offset = self.pos & 0xFF
        if USE_NUMPY:
            data = np.frombuffer(raw, dtype=np.uint8)
            idx = ((np.arange(count, dtype=np.uint32) + offset) & 0xFF).astype(np.uint8)
            out = (data ^ idx).tobytes()
        else:
            out = bytes((b ^ ((offset + i) & 0xFF)) for i, b in enumerate(raw))

        self.pos += count
        return out

    def close(self):
        self.f.close()


def stream_entry(reader: XorReader, size: int, dest: Path, chunk_size: int, progress_cb=None):
    """Decode and write `size` bytes from reader to dest, in bounded chunks."""
    remaining = size
    with open(dest, "wb") as of:
        while remaining > 0:
            n = min(chunk_size, remaining)
            chunk = reader.read(n)
            if not chunk:
                raise EOFError(f"Unexpected end of archive while extracting {dest}")
            of.write(chunk)
            remaining -= len(chunk)
            if progress_cb:
                progress_cb(len(chunk))


def extract_aafc(input_path: Path, out_dir: Path, chunk_size: int = DEFAULT_CHUNK_SIZE):
    out_dir.mkdir(parents=True, exist_ok=True)
    file_size = input_path.stat().st_size

    reader = XorReader(input_path)
    try:
        magic = reader.read(4)
        if magic != b"AAFC":
            raise ValueError(
                f"Not an AAFC archive (magic was {magic!r}, expected b'AAFC'). "
                "The XOR decoding may have failed, or this isn't the right file."
            )

        reader.seek(0x10)
        num_files = unpack(">I", reader.read(4))[0]

        # --- Pass 1: read the *entire* table of contents up front. -------
        # TOC entries are packed back-to-back; the data for all of them
        # lives in one contiguous block that starts only after the last
        # TOC entry -- it is NOT interleaved one-entry-header/one-entry-data
        # as the offline reference script assumed. (Confirmed empirically:
        # the sum of every entry's declared size exactly equals the number
        # of bytes remaining in the file after the TOC.)
        toc = []
        for i in range(num_files):
            entry_start = reader.pos
            namelen = unpack(">I", reader.read(4))[0]

            # Sanity check: a corrupted/misaligned parse tends to produce an
            # absurd name length, which would otherwise try to read gigabytes
            # into memory. Bail out with a useful diagnostic instead.
            if namelen > 4096:
                raise ValueError(
                    f"Entry {i}/{num_files}: implausible name length {namelen} "
                    f"at archive offset {entry_start}. The TOC parsing is "
                    f"likely desynced (a previous entry's fields may be "
                    f"misinterpreted) rather than this being a real entry."
                )

            name = reader.read(namelen * 2).decode("utf-16-be", errors="replace")
            unknown, size = unpack(">II", reader.read(8))

            if not name:
                print(
                    f"\nWarning: TOC entry {i}/{num_files} has an empty name "
                    f"(unknown={unknown}, size={size}) at offset {entry_start}; "
                    f"skipping. This usually means the archive layout doesn't "
                    f"match what this script expects.",
                    file=sys.stderr,
                )
                continue

            # Normalize into a safe relative path under out_dir
            rel_path = Path(*[p for p in name.split("/") if p not in ("", ".", "..")])
            is_dir = name.endswith("/") and size == 0
            toc.append((i, rel_path, size, is_dir))

        total_data_size = sum(size for _, _, size, is_dir in toc if not is_dir)
        remaining_in_file = file_size - reader.pos
        if total_data_size > remaining_in_file:
            raise ValueError(
                f"TOC declares {total_data_size} bytes of file data, but only "
                f"{remaining_in_file} bytes remain in the archive after the "
                f"TOC (offset {reader.pos}). Parsing is likely desynced -- "
                f"double check the archive layout assumptions in this script."
            )

        # --- Pass 2: stream the contiguous data section against the TOC. -
        # The reader is now positioned exactly at the start of the data
        # section (right after the last TOC entry), so entries can be
        # extracted in TOC order with no seeking.
        bytes_done = 0

        def progress(n):
            nonlocal bytes_done
            bytes_done += n
            done_mb = bytes_done / (1024 * 1024)
            total_mb = total_data_size / (1024 * 1024)
            print(f"\r{done_mb:.1f} / {total_mb:.1f} MB", end="", flush=True)

        extracted = 0
        for i, rel_path, size, is_dir in toc:
            if is_dir:
                (out_dir / rel_path).mkdir(parents=True, exist_ok=True)
                continue

            dest = out_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            print(f"\n{rel_path.as_posix()}")
            stream_entry(reader, size, dest, chunk_size, progress_cb=progress)
            extracted += 1

        skipped = num_files - len(toc)
        print(f"\nExtracted {extracted} file(s) to {out_dir}"
              + (f" ({skipped} empty/garbage entr{'y' if skipped == 1 else 'ies'} skipped)" if skipped else ""))

        trailing = file_size - reader.pos
        if trailing > 0:
            print(
                f"Note: {trailing} bytes at the end of the archive (offset "
                f"{reader.pos} onward) were not referenced by any TOC entry. "
                f"This may just be padding, or it may be a footer/extra data "
                f"the TOC format doesn't describe -- worth a manual look if "
                f"you're missing content.",
                file=sys.stderr,
            )
    finally:
        reader.close()


def main():
    parser = argparse.ArgumentParser(
        description="Decode an XOR-obfuscated AAFC archive and extract its "
        "contents in a single streaming pass."
    )
    parser.add_argument("input", type=Path, help="Path to the XOR-encoded archive file")
    parser.add_argument("output", type=Path, help="Folder to extract files into")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Max bytes read/written at a time per file entry (default {DEFAULT_CHUNK_SIZE})",
    )
    parser.add_argument(
        "--no-numpy",
        action="store_true",
        help="Force the pure-Python XOR loop even if numpy is available "
        "(slower, but useful for ruling out a numpy-related crash)",
    )
    args = parser.parse_args()

    global USE_NUMPY
    if args.no_numpy:
        USE_NUMPY = False

    if not USE_NUMPY:
        reason = "disabled via --no-numpy" if args.no_numpy else "numpy not found"
        print(
            f"Note: {reason}, falling back to slower pure-Python XOR loop.",
            file=sys.stderr,
        )

    extract_aafc(args.input, args.output, args.chunk_size)


if __name__ == "__main__":
    main()
