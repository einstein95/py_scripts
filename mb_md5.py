#!/usr/bin/env python3
import argparse
import hashlib
import re
from pathlib import Path
import struct

import macresources


def check_pjver(ver: int) -> int:
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
            new_name += f"\x81{chr(0x80 + ord(char))}"
        else:
            new_name += char
    return new_name


def needs_punyencoding(orig: str) -> bool:
    return (
        not orig.isascii()
        or orig != escape_string(orig)
        or orig.endswith(" ")
        or orig.endswith(".")
    )


parser = argparse.ArgumentParser(description="Process some files.")
parser.add_argument("file_path", type=Path)
parser.add_argument("--data-fork", action="store_true")
parser.add_argument("--version", action="store_true")
parser.add_argument("--wage", action="store_true")
args = parser.parse_args()

pjver = "0"
with args.file_path.open(mode="rb") as f:
    f.seek(0x53)
    datalen, rsrclen = struct.unpack(">II", f.read(8))
    if not rsrclen:
        f.seek(0x80)
        readsize = datalen
        rsrcoff = 0
    else:
        rsrcoff = 0x80 + datalen
        f.seek(rsrcoff + -datalen % 0x80)  # macbinary header + data fork + padding
        tmpoff = f.tell()
        m = list(macresources.parse_file(f.read()))
        for r in m:
            if r.type in [b"XCOD", b"XCMD", b"XFCN"]:
                print(f'{r.type.decode("mac-roman")}_{r.id:<5} {r.name}')

        if args.version:
            try:
                f.seek(rsrcoff - 0x1C)
                projoff = struct.unpack(">I", f.read(4))[0]
                f.seek(0x80 + projoff + 4)
                rifxoff = struct.unpack(">I", f.read(4))[0]
            except struct.error:
                vers = [i for i in m if i.type == b"vers" and i.id == 1]
                old_vers = [i for i in m if i.type == b"MMTE" and i.id == 0]
                if not vers and not old_vers:
                    raise ValueError("!!! no version !!!")
                if not old_vers:
                    digits = [
                        (byte >> 4) * 10 + (byte & 0x0F) for byte in bytes(vers[0])[:2]
                    ]
                    ver = digits[0] * 100 + digits[1]
                else:
                    digits = bytes(old_vers[0][1:]).decode("macroman").split()[0]
                    match = re.search(r"^[\d\.]+", digits)
                    if match:
                        ver = match.group(0)
                    else:
                        raise ValueError("???")
                    pjver = int(float(ver) * 100)

        f.seek(tmpoff)
        rsrcoff, rsrclen = struct.unpack(">I4xI", f.read(0xC))
        f.seek(rsrcoff - 0xC, 1)
        readsize = datalen if args.data_fork else rsrclen
    maxsize = 2 * 1024 * 1024 if args.wage else 5000
    md5hash = hashlib.md5(f.read(min(readsize, maxsize))).hexdigest()

filename = args.file_path.name
if needs_punyencoding(filename):
    filename = "xn--" + escape_string(filename).encode("punycode").decode("ascii")

prefix = "d:" if args.data_fork else "r:"
prefix = "" if args.wage else prefix
fields = [f'"{filename}"', f'"{prefix}{md5hash}"', str(readsize)] + (
    [str(pjver)] if args.version else []
)
print(", ".join(fields))
