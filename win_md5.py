#!/usr/bin/env python3
"""
Extract a hash for ScummVM's detection table from a Director EXE
"""
import argparse
import struct
from hashlib import md5
from pathlib import Path

SPECIAL_SYMBOLS = frozenset('/":*|\\?%<>\x7f')
VERSION_MAP = [
    (0x79F, 1201),
    (0x783, 1200),
    (0x782, 1150),
    (0x781, 1100),
    (0x73B, 1000),
    (0x6A4, 850),
    (0x582, 800),
    (0x4C8, 700),
    (0x4C2, 600),
    (0x4C1, 501),
    (0x4B1, 500),
    (0x45D, 404),
    (0x45B, 400),
    (0x405, 310),
    (0x404, 300),
]


def check_pjver(ver: int | None) -> int:
    """Map project version to release number using binary search."""
    if not ver:
        return 0
    for threshold, version in VERSION_MAP:
        if ver >= threshold:
            return version
    return 200


def escape_string(s: str) -> str:
    """Escape special characters for punycode encoding."""
    result = []
    for char in s:
        if char == "\x81":
            result.append("\x81\x79")
        elif char in SPECIAL_SYMBOLS or ord(char) < 0x20:
            result.append("\x81")
            result.append(chr(0x80 + ord(char)))
        else:
            result.append(char)
    return "".join(result)


def needs_punyencoding(s: str) -> bool:
    """Check if string needs punycode encoding."""
    if s and s[-1] in " .":
        return True
    return any(ord(c) < 0x20 or ord(c) >= 0x80 or c in SPECIAL_SYMBOLS for c in s)


def extract_version(f) -> int:
    """Extract project version from file."""
    try:
        # Find project and RIFX offsets
        f.seek(-4, 2)
        projoff = struct.unpack("<I", f.read(4))[0]
        f.seek(projoff + 4)
        rifxoff = struct.unpack("<I", f.read(4))[0]

        # Search for version in APPLimap
        f.seek(rifxoff)
        data = f.read()

        for marker in (b"LPPApami", b"APPLimap"):
            off = data.find(marker)
            if off > 0:
                f.seek(rifxoff + off + 0x14)
                pjver = struct.unpack("<I", f.read(4))[0]
                if pjver:
                    return pjver
                break

        # Fallback to VWCF
        off = data.find(b"FCWV")
        if off >= 0:
            f.seek(rifxoff + off + 4)
            _, vwcfoff = struct.unpack("<II", f.read(8))
            f.seek(vwcfoff + 0x2C)
            return struct.unpack(">H", f.read(2))[0]
    except (struct.error, OSError):
        pass

    return 0x404


def compute_hash(f, is_head: bool, chunk_size: int = 5000) -> str:
    """Compute MD5 hash of file or chunk."""
    f.seek(0, 2)
    size = f.tell()

    if size <= chunk_size:
        f.seek(0)
        return md5(f.read()).hexdigest()

    if is_head:
        f.seek(0)
    else:
        f.seek(-chunk_size, 2)

    return md5(f.read(chunk_size)).hexdigest()


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Process some files.")
    parser.add_argument("file_path", type=Path)
    parser.add_argument("--head", action="store_true")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()

    if not args.file_path.exists():
        parser.error(f"File not found: {args.file_path}")

    with args.file_path.open("rb") as f:
        pjver = extract_version(f) if args.version else None
        prefix = "h:" if args.head else "t:"
        m = compute_hash(f, args.head)

        f.seek(0, 2)
        size = f.tell()

    fn = args.file_path.name
    if needs_punyencoding(fn):
        fn = "xn--" + escape_string(fn).encode("punycode").decode("ascii")

    if args.version:
        version = check_pjver(pjver)
        print(f'"{fn}", "{prefix}{m}", {size}, {version}')
    else:
        print(f'"{fn}", "{prefix}{m}", {size}')


if __name__ == "__main__":
    main()
