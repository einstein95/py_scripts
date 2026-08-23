#!/usr/bin/env python3
"""
KRO ("Burp") archive extractor.

Reverse engineered from the open/directory-read routine (sub_441CEF and
helpers) found in a DOS game executable (Prisoner of Ice, Infogrames 1995).

File format
-----------
Header (8 bytes):
    char[4]   magic       "Burp"
    uint32    count       LE, number of directory entries

Directory table (count * 20 bytes), immediately follows the header:
    uint32    orig_size   uncompressed size of the resource
    uint32    size        size of the resource as stored in the file
    uint32    reserved    always 0 in every sample seen
    uint32    offset      absolute file offset of the resource's data
    uint32    type        0 = stored raw      (orig_size == size)
                           4 = stored packed  (orig_size != size,
                               compression algorithm not yet identified)

Data section: resource bytes packed contiguously back-to-back, starting
immediately after the directory table, in the same order as the
directory entries (offset[i] + size[i] == offset[i+1]).

Note on the disassembly this was derived from: the routine that opens a
.KRO file also supports an older variant where the "Burp" header/count
sits at an offset given by the *last 4 bytes of the file* rather than at
offset 0 (i.e. a footer-based layout used by some other title/version).
None of the four sample files in the demo set use that layout - they all
have the header at offset 0 - so this script only implements the
offset-0 case. See parse_kro() if you need to add footer support.

Type 4 entries are raw DEFLATE streams (no zlib/gzip wrapper - i.e.
zlib.decompress(data, -15)). Confirmed against every type-4 entry in
the demo set: decompressed length matches orig_size exactly every time.
"""
import argparse
import json
import os
import struct
import sys
import zlib

MAGIC = b"Burp"
ENTRY_SIZE = 20
HEADER_SIZE = 8


def parse_kro(path):
    with open(path, "rb") as f:
        data = f.read()

    if data[:4] == MAGIC:
        header_offset = 0
    else:
        # Footer-based variant: last 4 bytes of the file hold the
        # offset where the "Burp" header actually lives.
        (footer_offset,) = struct.unpack("<I", data[-4:])
        if data[footer_offset : footer_offset + 4] == MAGIC:
            header_offset = footer_offset
        else:
            raise ValueError(
                f"{path}: not a recognized KRO/Burp file "
                f"(bad magic {data[:4]!r}, and no valid "
                f"footer-referenced header found)"
            )

    count = struct.unpack_from("<I", data, header_offset + 4)[0]
    entries = []
    base = header_offset + HEADER_SIZE
    for i in range(count):
        chunk = data[base + i * ENTRY_SIZE : base + (i + 1) * ENTRY_SIZE]
        if len(chunk) < ENTRY_SIZE:
            raise ValueError(f"{path}: truncated directory table at entry {i}")
        orig_size, size, reserved, offset, typ = struct.unpack("<5I", chunk)
        entries.append(
            {
                "index": i,
                "orig_size": orig_size,
                "size": size,
                "reserved": reserved,
                "offset": offset,
                "type": typ,
            }
        )
    return data, count, entries, header_offset


def extract(path, outdir, write_json=True, keep_raw=False):
    data, count, entries, header_offset = parse_kro(path)
    base_name = os.path.splitext(os.path.basename(path))[0]
    target_dir = os.path.join(outdir, base_name)
    os.makedirs(target_dir, exist_ok=True)

    manifest = []
    ndigits = max(4, len(str(count)))
    n_decode_failed = 0
    for e in entries:
        raw = data[e["offset"] : e["offset"] + e["size"]]
        if len(raw) != e["size"]:
            print(
                f"  warning: entry {e['index']} truncated "
                f"({len(raw)}/{e['size']} bytes)",
                file=sys.stderr,
            )

        entry_info = dict(e)
        entry_info["compressed"] = e["type"] != 0

        if e["type"] == 0:
            # Stored raw.
            payload = raw
            fname = f"{e['index']:0{ndigits}d}.bin"
        else:
            # Type 4 (and, cautiously, any other non-zero type): raw
            # DEFLATE stream, no zlib/gzip wrapper.
            try:
                payload = zlib.decompress(raw, -15)
                if payload != raw and len(payload) != e["orig_size"]:
                    print(
                        f"  warning: entry {e['index']} decompressed "
                        f"size {len(payload)} != orig_size {e['orig_size']}",
                        file=sys.stderr,
                    )
                fname = f"{e['index']:0{ndigits}d}.bin"
            except zlib.error as ex:
                n_decode_failed += 1
                print(
                    f"  warning: entry {e['index']} failed to inflate "
                    f"({ex}); writing compressed bytes instead",
                    file=sys.stderr,
                )
                payload = raw
                fname = f"{e['index']:0{ndigits}d}_type{e['type']}_stillpacked.bin"
            entry_info["decompressed"] = fname == f"{e['index']:0{ndigits}d}.bin"

            if keep_raw:
                raw_fname = f"{e['index']:0{ndigits}d}_type{e['type']}.raw"
                with open(os.path.join(target_dir, raw_fname), "wb") as rf:
                    rf.write(raw)
                entry_info["raw_file"] = raw_fname

        with open(os.path.join(target_dir, fname), "wb") as out:
            out.write(payload)
        entry_info["file"] = fname
        manifest.append(entry_info)

    if write_json:
        with open(os.path.join(target_dir, "_manifest.json"), "w") as jf:
            json.dump(
                {
                    "source": os.path.basename(path),
                    "header_offset": header_offset,
                    "count": count,
                    "entries": manifest,
                },
                jf,
                indent=2,
            )

    n_compressed = sum(1 for e in manifest if e["compressed"])
    msg = (
        f"{path}: extracted {count} entries to {target_dir}/ "
        f"({n_compressed} inflated from deflate, {count - n_compressed} raw)"
    )
    if n_decode_failed:
        msg += f" - {n_decode_failed} FAILED to inflate, kept compressed"
    print(msg)
    return manifest


def main():
    ap = argparse.ArgumentParser(description='Extract .KRO ("Burp") archives')
    ap.add_argument("files", nargs="+", help=".KRO file(s) to extract")
    ap.add_argument("-o", "--outdir", default="extracted", help="output directory")
    ap.add_argument(
        "--list", action="store_true", help="only list contents, don't extract"
    )
    ap.add_argument(
        "--keep-raw",
        action="store_true",
        help="also save the still-compressed bytes for type 4 entries "
        "(alongside the inflated output)",
    )
    args = ap.parse_args()

    for path in args.files:
        if args.list:
            data, count, entries, header_offset = parse_kro(path)
            print(f"\n{path}  ({count} entries, header @ 0x{header_offset:X})")
            print(
                f"{'idx':>5} {'offset':>10} {'size':>10} {'orig_size':>10} {'type':>5}"
            )
            for e in entries:
                print(
                    f"{e['index']:>5} {e['offset']:>10} {e['size']:>10} "
                    f"{e['orig_size']:>10} {e['type']:>5}"
                )
        else:
            extract(path, args.outdir, keep_raw=args.keep_raw)


if __name__ == "__main__":
    main()
