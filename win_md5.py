#!/usr/bin/env python3
import argparse
from hashlib import md5
from pathlib import Path
from struct import unpack


def check_pjver(ver):
    if ver >= 0x79F:
        return 1201
    elif ver >= 0x783:
        return 1200
    elif ver >= 0x782:
        return 1150
    elif ver >= 0x781:
        return 1100
    elif ver >= 0x73B:
        return 1000
    elif ver >= 0x6A4:
        return 850
    elif ver >= 0x582:
        return 800
    elif ver >= 0x4C8:
        return 700
    elif ver >= 0x4C2:
        return 600
    elif ver >= 0x4C1:
        return 501
    elif ver >= 0x4B1:
        return 500
    elif ver >= 0x45D:
        return 404
    elif ver >= 0x45B:
        return 400
    elif ver >= 0x405:
        return 310
    elif ver >= 0x404:
        return 300
    else:
        return 200


def escape_string(s: str) -> str:
    new_name = ""
    for char in s:
        if char == "\x81":
            new_name += "\x81\x79"
        elif char in '/":*|\\?%<>' or ord(char) < 0x20:
            new_name += "\x81" + chr(0x80 + ord(char))
        else:
            new_name += char
    return new_name


def needs_punyencoding(orig: str) -> bool:
    if not orig.isascii():
        return True
    if orig != escape_string(orig):
        return True
    if orig[-1] in " .":
        return True
    return False


parser = argparse.ArgumentParser(description="Process some files.")
parser.add_argument("file_path", type=Path)
parser.add_argument("--head", action="store_true")
parser.add_argument("--version", action="store_true")
args = parser.parse_args()

assert args.file_path.exists()

with args.file_path.open("rb") as f:
    if args.version:
        tmpoff = f.tell()
        f.seek(-4, 2)
        projoff = unpack("<I", f.read(4))[0]
        f.seek(projoff + 4)
        rifxoff = unpack("<I", f.read(4))[0]
        f.seek(rifxoff)
        d = f.read()
        off = d.find(b"LPPApami")
        if off < 0:
            off = d.find(b"APPLimap")
        if off > 0:
            f.seek(rifxoff + off + 0x14)
            pjver = unpack("<I", f.read(4))[0]
            if not pjver:
                f.seek(rifxoff)
                off = d.find(b"FCWV")
                f.seek(rifxoff + off + 4)
                vwcflen, vwcfoff = unpack("<II", f.read(8))
                f.seek(vwcfoff + 0x2C)
                pjver = unpack(">H", f.read(2))[0]
            f.seek(tmpoff)
        else:
            pjver = 0x404

    f.seek(0, 2)
    size = f.tell()
    prefix = "h:" if args.head else "t:"
    if 5000 > size:
        f.seek(0)
        m = md5(f.read()).hexdigest()
    else:
        if args.head:
            f.seek(0)
        else:
            f.seek(-5000, 2)
        m = md5(f.read(5000)).hexdigest()

fn = args.file_path.name
if needs_punyencoding(fn):
    fn = "xn--" + escape_string(fn).encode("punycode").decode("ascii")

if args.version:
    print(f'"{fn}", "{prefix}{m}", {size}, {check_pjver(pjver)}')
else:
    print(f'"{fn}", "{prefix}{m}", {size}')
