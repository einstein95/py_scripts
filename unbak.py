#!/usr/bin/env python3
# See https://www.downtowndougbrown.com/2013/06/legacy-apple-backup-file-format-on-floppy-disks/
import os
import struct
import sys
from binascii import crc_hqx
from pathlib import Path
from typing import Tuple


def file_to_macbin(datalen, rsrclen, crdate, mddate, type, creator, flags, name):
    oldFlags = flags >> 8
    newFlags = flags & 255
    macbin = struct.pack(
        ">xB63s4s4sBxHHHBxIIIIHB14xIHBB",
        len(name),
        name,
        type,
        creator,
        oldFlags,
        0,
        0,
        0,
        oldFlags & 128,
        datalen,
        rsrclen,
        crdate,
        mddate,
        0,
        newFlags,
        0,
        0,
        129,
        129,
    )
    macbin += struct.pack(">H2x", crc_hqx(macbin, 0))
    return macbin


def punyencode(orig: str) -> str:
    """
    Punyencode strings

    - escape special characters and
    - ensure filenames can't end in a space or dot
    """
    s = escape_string(orig)
    encoded = s.encode("punycode").decode("ascii")
    # punyencoding adds an '-' at the end when there are no special chars
    # don't use it for comparing
    compare = encoded
    if encoded.endswith("-"):
        compare = encoded[:-1]
    if orig != compare or compare[-1] in " .":
        return "xn--" + encoded
    return orig


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
    if orig != escape_string(orig):
        return True
    if orig[-1] in " .":
        return True
    return False


f = open(sys.argv[1], "rb")

magic, disk_n, n_disks, _, _, volume_name, _, size = struct.unpack(
    ">2x4sHHII32pII454x", f.read(0x200)
)
assert magic == b"CMWL"

# Skip boot blocks
f.read(0x400)

size -= 0x600

while size:
    (
        magic,
        _,
        _,
        _,
        filename,
        part_n,
        folder_flags,
        valid,
        tcode,
        ccode,
        flags,
        created,
        modified,
        data_length,
        resource_length,
        data_length_this_disk,
        resource_length_this_disk,
        path_length,
    ) = struct.unpack(">2x4sHII32pHBB4s4sH24xIIIIIIH", f.read(0x70))
    assert magic == b"RLDW"
    is_folder = folder_flags & (1 << 7) != 0
    full_path = f.read(path_length)
    data_fork = f.read(data_length_this_disk)
    resource_fork = f.read(resource_length_this_disk)
    total_size = 0x70 + path_length + data_length_this_disk + resource_length_this_disk
    padding = 0x200 - (total_size % 0x200) if (total_size % 0x200) else 0
    f.read(padding)
    size -= total_size + padding

    out_path = Path()
    nix_path = Path(*full_path.decode("macroman").split(":"))
    for el in nix_path.parts:
        if needs_punyencoding(el):
            el = punyencode(el)

        out_path /= el

    os.makedirs(out_path if is_folder else out_path.parent, exist_ok=True)

    print(
        "writing to {} {}, part {}, df={} rf={}".format(
            " folder" if is_folder else "",
            out_path,
            part_n,
            len(data_fork),
            len(resource_fork),
        )
    )

    if not is_folder:
        if part_n > 1:
            with open(out_path, "ab") as of:
                if data_fork:
                    of.write(data_fork)
                    of.write(b"\x00" * (-data_length % 128))
                if resource_fork:
                    of.write(resource_fork)
                    of.write(b"\x00" * (-resource_length % 128))

        else:
            with open(out_path, "wb") as of:
                of.write(
                    file_to_macbin(
                        data_length,
                        resource_length,
                        created,
                        modified,
                        tcode,
                        ccode,
                        flags,
                        filename,
                    )
                )
                if data_fork:
                    of.write(data_fork)
                    if data_length == data_length_this_disk:
                        of.write(b"\x00" * (-data_length % 128))
                if resource_fork:
                    of.write(resource_fork)
                    if resource_length == resource_length_this_disk:
                        of.write(b"\x00" * (-resource_length % 128))

    modified -= 2082844800
    os.utime(out_path, (modified, modified))
