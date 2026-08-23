#!/usr/bin/env python3
"""
dxa_extract.py - Extractor for DX Library (DxLib) ".dxa" archives

Reimplements the read path of DxArchive_.cpp/.h (DX Library archive format,
"Ver 3.24f", archive format version 0x0008) in pure Python:

  * DXARC_HEAD / DXARC_FILEHEAD / DXARC_DIRECTORY parsing
  * XOR "encryption" (DXA_KeyCreate / DXA_KeyConv)
  * Custom LZ77-style decompression (DXA_Decode)
  * Adaptive Huffman decompression (Huffman_Decode)
  * Per-file key derivation (password + filename + parent directory names)

Only archive format version 0x0008 (the version emitted by recent DxLib
versions) is supported, matching the reference source.

Usage:
    python3 dxa_extract.py archive.dxa                  # extract next to archive
    python3 dxa_extract.py archive.dxa -o out_dir        # extract to out_dir
    python3 dxa_extract.py archive.dxa -l                # just list contents
    python3 dxa_extract.py archive.dxa -p mypassword     # custom archive password
                                                          # (only needed if the
                                                          # game set one via
                                                          # DXA_DIR_SetKeyString /
                                                          # SetDXArchiveKeyString)

Notes:
  * If no password is supplied, the DxLib default key string is used
    (this is what almost all DxLib games use unless they explicitly set
    their own password).
  * Filenames are decoded on a best-effort basis (utf-8, then Shift_JIS,
    then latin-1) since the archive's declared character-code field is not
    always trustworthy across DxLib versions; decryption itself operates on
    raw bytes and does not depend on the text encoding.
"""

import argparse
import os
import struct
import sys
import zlib
from pathlib import Path

# --------------------------------------------------------------------------
# Constants (from DxArchive_.h / DxArchive_.cpp)
# --------------------------------------------------------------------------

DXA_KEY_BYTES = 7
NONE_PAL = 0xFFFFFFFFFFFFFFFF
FILE_ATTRIBUTE_DIRECTORY = 0x10

DXA_FLAG_NO_KEY = 0x00000001
DXA_FLAG_NO_HEAD_PRESS = 0x00000002

MIN_COMPRESS = 4

# "DXBDXARC" - the literal bytes of DefaultKeyString in DxArchive_.cpp
DEFAULT_KEY_STRING = bytes([0x44, 0x58, 0x42, 0x44, 0x58, 0x41, 0x52, 0x43])

DXARC_HEAD_STRUCT = struct.Struct("<HHIQQQQIIB15s")  # 64 bytes (Ver 0x0008)
DXARC_FILEHEAD_STRUCT = struct.Struct("<QQQQQQQQQ")  # 72 bytes (Ver 0x0008)
DXARC_DIRECTORY_STRUCT = struct.Struct("<QQQQ")  # 32 bytes

assert DXARC_HEAD_STRUCT.size == 64
assert DXARC_FILEHEAD_STRUCT.size == 72
assert DXARC_DIRECTORY_STRUCT.size == 32


class DxaError(Exception):
    pass


# --------------------------------------------------------------------------
# Key derivation / XOR "encryption"
# --------------------------------------------------------------------------


def dxa_key_create(source: bytes) -> bytes:
    """Port of DXA_KeyCreate(): builds the 7-byte working key from a
    password / per-file key string using CRC32 of the even/odd-indexed
    bytes of the source string."""
    if len(source) < 4:
        source = source + DEFAULT_KEY_STRING

    even = source[0::2]
    odd = source[1::2]

    crc0 = zlib.crc32(even) & 0xFFFFFFFF
    crc1 = zlib.crc32(odd) & 0xFFFFFFFF

    return bytes(
        [
            crc0 & 0xFF,
            (crc0 >> 8) & 0xFF,
            (crc0 >> 16) & 0xFF,
            (crc0 >> 24) & 0xFF,
            crc1 & 0xFF,
            (crc1 >> 8) & 0xFF,
            (crc1 >> 16) & 0xFF,
        ]
    )


def dxa_keyconv(data: bytes, position: int, key: bytes) -> bytes:
    """Port of DXA_KeyConv(): XORs `data` against a repeating 7-byte key
    stream, where `position` selects the starting phase within the key."""
    n = len(data)
    if n == 0:
        return data
    p0 = position % DXA_KEY_BYTES
    rotated = key[p0:] + key[:p0]
    reps = (n // DXA_KEY_BYTES) + 2
    keystream = (rotated * reps)[:n]
    return (int.from_bytes(data, "big") ^ int.from_bytes(keystream, "big")).to_bytes(
        n, "big"
    )


# --------------------------------------------------------------------------
# LZ decompression (DXA_Decode)
# --------------------------------------------------------------------------


def dxa_decode(src: bytes) -> bytes:
    """Port of DXA_Decode(): custom LZ77-style decompressor used for both
    the archive header table and (optionally) file data."""
    if len(src) < 9:
        raise DxaError("LZ stream too short")

    destsize = int.from_bytes(src[0:4], "little")
    srcsize_field = int.from_bytes(src[4:8], "little")
    keycode = src[8]

    srcsize = srcsize_field - 9
    out = bytearray()
    sp = 9
    remaining = srcsize
    n = len(src)

    while remaining > 0:
        if sp >= n:
            raise DxaError("LZ stream truncated")
        if src[sp] != keycode:
            out.append(src[sp])
            sp += 1
            remaining -= 1
            continue

        if src[sp + 1] == keycode:
            out.append(keycode)
            sp += 2
            remaining -= 2
            continue

        code = src[sp + 1]
        if code > keycode:
            code -= 1
        sp += 2
        remaining -= 2

        conbo = code >> 3
        if code & 0x4:
            conbo |= src[sp] << 5
            sp += 1
            remaining -= 1
        conbo += MIN_COMPRESS

        indexsize = code & 0x3
        if indexsize == 0:
            index = src[sp]
            sp += 1
            remaining -= 1
        elif indexsize == 1:
            index = src[sp] | (src[sp + 1] << 8)
            sp += 2
            remaining -= 2
        else:
            index = src[sp] | (src[sp + 1] << 8) | (src[sp + 2] << 16)
            sp += 3
            remaining -= 3
        index += 1

        if index < conbo:
            num = index
            while conbo > num:
                out += out[-num:]
                conbo -= num
                num += num
            if conbo != 0:
                out += out[-num:][:conbo]
        else:
            start = len(out) - index
            out += out[start : start + conbo]

    if len(out) != destsize:
        # Not fatal necessarily, but flag it - helps catch key/format errors early.
        raise DxaError(f"LZ decode size mismatch: expected {destsize}, got {len(out)}")

    return bytes(out)


# --------------------------------------------------------------------------
# Huffman decompression (Huffman_Decode)
# --------------------------------------------------------------------------


class _BitReaderMSB:
    """Reads bits MSB-first within each byte (matches BIT_STREAM / BitStream_Read)."""

    __slots__ = ("data", "pos")

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def read(self, n: int) -> int:
        v = 0
        data = self.data
        pos = self.pos
        for _ in range(n):
            byte = data[pos >> 3]
            bit = (byte >> (7 - (pos & 7))) & 1
            v = (v << 1) | bit
            pos += 1
        self.pos = pos
        return v

    def bytes_consumed(self) -> int:
        return (self.pos + 7) // 8


def huffman_decode(press: bytes) -> bytes:
    """Port of Huffman_Decode(): decodes an adaptive-Huffman-compressed
    buffer as produced by Huffman_Encode()."""
    br = _BitReaderMSB(press)

    nbits = br.read(6) + 1
    original_size = br.read(nbits)

    nbits2 = br.read(6) + 1
    br.read(nbits2)  # compressed size, unused for decoding

    weight = [0] * 256
    for i in range(256):
        bn = (br.read(3) + 1) * 2
        minus = br.read(1)
        save = br.read(bn)
        if i == 0:
            weight[i] = save & 0xFFFF
        else:
            if minus:
                weight[i] = (weight[i - 1] - save) & 0xFFFF
            else:
                weight[i] = (weight[i - 1] + save) & 0xFFFF

    head_size = br.bytes_consumed()

    if original_size == 0:
        return b""

    total_nodes = 256 + 255
    node_weight = [0] * total_nodes
    child0 = [-1] * total_nodes
    child1 = [-1] * total_nodes
    parent = [-1] * total_nodes

    for i in range(256):
        node_weight[i] = weight[i]

    data_num = 256
    node_num = 256
    while data_num > 1:
        min1 = -1
        min2 = -1
        cnt = 0
        idx = 0
        while cnt < data_num:
            if parent[idx] != -1:
                idx += 1
                continue
            cnt += 1
            if min1 == -1 or node_weight[min1] > node_weight[idx]:
                min2 = min1
                min1 = idx
            else:
                if min2 == -1 or node_weight[min2] > node_weight[idx]:
                    min2 = idx
            idx += 1

        parent[node_num] = -1
        node_weight[node_num] = node_weight[min1] + node_weight[min2]
        child0[node_num] = min1
        child1[node_num] = min2
        parent[min1] = node_num
        parent[min2] = node_num
        node_num += 1
        data_num -= 1

    root = node_num - 1

    body = press[head_size:] + b"\x00" * 16  # safety padding for the tail
    out = bytearray(original_size)
    bitpos = 0

    for k in range(original_size):
        node = root
        while node > 255:
            byte = body[bitpos >> 3]
            bit = (byte >> (bitpos & 7)) & 1
            bitpos += 1
            node = child1[node] if bit else child0[node]
        out[k] = node

    return bytes(out)


# --------------------------------------------------------------------------
# Archive parsing / extraction
# --------------------------------------------------------------------------


class DxArchiveEntry:
    __slots__ = (
        "name_addr",
        "attributes",
        "data_addr",
        "data_size",
        "press_size",
        "huff_size",
        "is_dir",
    )

    def __init__(self, raw: bytes):
        (
            name_addr,
            attributes,
            _create,
            _last_access,
            _last_write,
            data_addr,
            data_size,
            press_size,
            huff_size,
        ) = DXARC_FILEHEAD_STRUCT.unpack(raw)
        self.name_addr = name_addr
        self.attributes = attributes
        self.data_addr = data_addr
        self.data_size = data_size
        self.press_size = None if press_size == NONE_PAL else press_size
        self.huff_size = None if huff_size == NONE_PAL else huff_size
        self.is_dir = bool(attributes & FILE_ATTRIBUTE_DIRECTORY)


class DxArchive:
    def __init__(self, path, password=None, verbose=False):
        self.path = Path(path)
        self.verbose = verbose
        with open(self.path, "rb") as f:
            self.data = f.read()

        if isinstance(password, str):
            password = password.encode("utf-8")
        self.password = password if password else DEFAULT_KEY_STRING

        self._parse_header()

    def log(self, *a):
        if self.verbose:
            print(*a, file=sys.stderr)

    # ---- header -----------------------------------------------------

    def _parse_header(self):
        data = self.data
        if len(data) < 64:
            raise DxaError("File too small to be a DX archive")
        if data[0:2] != b"DX":
            raise DxaError("Bad signature (not a DX archive)")

        (
            head_id,
            version,
            head_size,
            data_start,
            name_table_start,
            file_table_start,
            dir_table_start,
            char_code_format,
            flags,
            huffman_kb,
            _reserve,
        ) = DXARC_HEAD_STRUCT.unpack(data[0:64])

        if version < 8:
            raise DxaError(
                f"Unsupported archive version 0x{version:04x}; "
                f"only version 0x0008 is supported by this tool"
            )

        self.version = version
        self.head_size = head_size
        self.data_start = data_start
        self.name_table_start = name_table_start
        self.file_table_rel = file_table_start
        self.dir_table_rel = dir_table_start
        self.char_code_format = char_code_format
        self.flags = flags
        self.huffman_kb = huffman_kb
        self.no_key = bool(flags & DXA_FLAG_NO_KEY)

        self.key = dxa_key_create(self.password)

        if flags & DXA_FLAG_NO_HEAD_PRESS:
            table = data[name_table_start : name_table_start + head_size]
            if not self.no_key:
                table = dxa_keyconv(table, 0, self.key)
        else:
            huff_head = data[name_table_start:]
            if not self.no_key:
                huff_head = dxa_keyconv(huff_head, 0, self.key)
            lz_head = huffman_decode(huff_head)
            table = dxa_decode(lz_head)

        self.table = table
        self.file_table_off = self.file_table_rel
        self.dir_table_off = self.dir_table_rel

    # ---- low level table access --------------------------------------

    def _get_directory(self, dir_off):
        raw = self.table[
            self.dir_table_off + dir_off : self.dir_table_off + dir_off + 32
        ]
        dir_addr, parent_addr, num, addr = DXARC_DIRECTORY_STRUCT.unpack(raw)
        return {
            "dir_addr": dir_addr,
            "parent_addr": parent_addr,
            "num": num,
            "addr": addr,
        }

    def _get_filehead(self, off):
        raw = self.table[self.file_table_off + off : self.file_table_off + off + 72]
        return DxArchiveEntry(raw)

    def _get_name_bytes(self, name_addr, real=True):
        base = self.table
        packnum = struct.unpack_from("<H", base, name_addr)[0]
        if real:
            start = name_addr + 4 + packnum * 4
        else:
            start = name_addr + 4
        end = base.index(b"\x00", start)
        return base[start:end]

    @staticmethod
    def _decode_name(raw: bytes) -> str:
        for enc in ("utf-8", "shift_jis", "cp1252"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return raw.decode("latin-1")

    # ---- per-file key ---------------------------------------------

    def _dir_name_chain(self, dir_off):
        chain = []
        d = self._get_directory(dir_off)
        if d["parent_addr"] == NONE_PAL:
            return chain
        while True:
            dfh = self._get_filehead(d["dir_addr"])
            chain.append(self._get_name_bytes(dfh.name_addr, real=False))
            dir_off = d["parent_addr"]
            d = self._get_directory(dir_off)
            if d["parent_addr"] == NONE_PAL:
                break
        return chain

    def _build_file_key(self, dir_off, fh: DxArchiveEntry):
        parts = [self.password, self._get_name_bytes(fh.name_addr, real=False)]
        parts.extend(self._dir_name_chain(dir_off))
        return dxa_key_create(b"".join(parts))

    # ---- file data extraction ---------------------------------------

    def _extract_file_data(self, dir_off, fh: DxArchiveEntry) -> bytes:
        data_size = fh.data_size
        press = fh.press_size
        huff = fh.huff_size
        edge_kb = self.huffman_kb
        offset = self.data_start + fh.data_addr

        if data_size == 0:
            return b""

        if huff is not None:
            if press is not None:
                if edge_kb != 0xFF and press > edge_kb * 1024 * 2:
                    raw_len = huff + (press - edge_kb * 1024 * 2)
                else:
                    raw_len = huff
            else:
                if edge_kb != 0xFF and data_size > edge_kb * 1024 * 2:
                    raw_len = huff + (data_size - edge_kb * 1024 * 2)
                else:
                    raw_len = huff
        elif press is not None:
            raw_len = press
        else:
            raw_len = data_size

        raw = self.data[offset : offset + raw_len]
        if not self.no_key:
            key = self._build_file_key(dir_off, fh)
            raw = dxa_keyconv(raw, data_size, key)

        if huff is not None:
            huff_blob = raw[:huff]
            if press is not None:
                if edge_kb != 0xFF and press > edge_kb * 1024 * 2:
                    middle = raw[huff : huff + (press - edge_kb * 1024 * 2)]
                    edges = huffman_decode(huff_blob)
                    front = edges[: edge_kb * 1024]
                    back = edges[edge_kb * 1024 : edge_kb * 1024 * 2]
                    lz_stream = front + middle + back
                else:
                    lz_stream = huffman_decode(huff_blob)
                final = dxa_decode(lz_stream)
            else:
                if edge_kb != 0xFF and data_size > edge_kb * 1024 * 2:
                    middle = raw[huff : huff + (data_size - edge_kb * 1024 * 2)]
                    edges = huffman_decode(huff_blob)
                    front = edges[: edge_kb * 1024]
                    back = edges[edge_kb * 1024 : edge_kb * 1024 * 2]
                    final = front + middle + back
                else:
                    final = huffman_decode(huff_blob)
        elif press is not None:
            final = dxa_decode(raw)
        else:
            final = raw

        if len(final) != data_size:
            raise DxaError(
                f"decoded size mismatch: expected {data_size}, got {len(final)}"
            )

        return final

    # ---- walking ------------------------------------------------------

    def walk(self, dir_off=0, prefix=""):
        """Yields (kind, path, dir_off, entry) for every file/dir in the archive.
        kind is 'file' or 'dir'."""
        d = self._get_directory(dir_off)
        for i in range(d["num"]):
            fh = self._get_filehead(d["addr"] + i * 72)
            name = self._decode_name(self._get_name_bytes(fh.name_addr, real=True))
            full = prefix + name
            if fh.is_dir:
                yield ("dir", full, dir_off, fh)
                yield from self.walk(fh.data_addr, full + "/")
            else:
                yield ("file", full, dir_off, fh)

    # ---- public API -----------------------------------------------

    def list(self):
        for kind, path, _dir_off, fh in self.walk():
            if kind == "file":
                yield (path, fh.data_size)

    def extract_all(self, out_dir):
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        count = 0
        for kind, path, dir_off, fh in self.walk():
            safe_path = self._sanitize(path)
            dest = out_dir / safe_path
            if kind == "dir":
                dest.mkdir(parents=True, exist_ok=True)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            self.log(f"extracting {path} ({fh.data_size} bytes)")
            data = self._extract_file_data(dir_off, fh)
            with open(dest, "wb") as out:
                out.write(data)
            count += 1
        return count

    @staticmethod
    def _sanitize(path: str) -> Path:
        # Prevent path traversal / absolute paths from a hostile archive.
        parts = []
        for part in path.replace("\\", "/").split("/"):
            if part in ("", ".", ".."):
                continue
            parts.append(part)
        return Path(*parts) if parts else Path("_")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description="Extract DX Library (DxLib) .dxa archives")
    ap.add_argument("archive", help="Path to the .dxa archive file")
    ap.add_argument(
        "-o", "--output", help="Output directory (default: <archive>_extracted)"
    )
    ap.add_argument("-p", "--password", help="Archive key string, if the game set one")
    ap.add_argument(
        "-l", "--list", action="store_true", help="List contents instead of extracting"
    )
    ap.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = ap.parse_args()

    try:
        arc = DxArchive(args.archive, password=args.password, verbose=args.verbose)
    except DxaError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.list:
        total = 0
        for path, size in arc.list():
            print(f"{size:>12}  {path}")
            total += 1
        print(f"\n{total} file(s)", file=sys.stderr)
        return

    out_dir = args.output or (str(Path(args.archive).with_suffix("")) + "_extracted")
    try:
        count = arc.extract_all(out_dir)
    except DxaError as e:
        print(f"error: {e}", file=sys.stderr)
        print(
            "This usually means the archive uses a custom password "
            "(try -p) or is not a version-0x0008 DX archive.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Extracted {count} file(s) to {out_dir}")


if __name__ == "__main__":
    main()
