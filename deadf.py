#!/usr/bin/env python3
# Data Fork            1  Data fork
# Resource Fork        2  Resource fork
# Real Name            3  File’s name as created on home file system
# Comment              4  Standard Macintosh comment
# Icon, B&W            5  Standard Macintosh black and white icon
# Icon, Color          6  Macintosh color icon
# File Dates Info      8  File creation date, modification date, and so on
# Finder Info          9  Standard Macintosh Finder information
# Macintosh File Info 10  Macintosh file information, attributes, and so on
# ProDOS File Info    11  ProDOS file information, attributes, and so on
# MS-DOS File Info    12  MS-DOS file information, attributes, and so on
# Short Name          13  AFP short name
# AFP File Info       14  AFP file information, attributes, and so on
# Directory ID        15  AFP directory ID
import os
import re
import struct
import sys
from binascii import crc_hqx
from urllib import parse


def file_to_macbin(datalen, rsrclen, crdate, mddate, type, creator, flags, name):
    oldFlags = flags >> 8
    newFlags = flags & 0xFF
    macbin = struct.pack(">x64p4s4sBxHHHBxIIIIHB14xIHBB",
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
        129
    )
    macbin += struct.pack('>H2x', crc_hqx(macbin, 0))
    return macbin


def escape_string(s: str) -> str:
    new_name = ""
    for char in s:
        if char == "\x81":
            new_name += "\x81\x79"
        elif char in '/":*|\\?%<>\x7f' or ord(char) < 0x20:
            new_name += "\x81" + chr(0x80 + ord(char))
        else:
            new_name += char
    return new_name


def punyencode(orig: str) -> str:
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


japanese = len(sys.argv) > 3 and sys.argv[3] == 'j'
f = open(sys.argv[1], 'rb')
assert f.read(4) in [b'\x00\x05\x16\x07', b'\x00\x05\x16\x00']
assert f.read(4) == b'\x00\x02\x00\x00'
f.seek(0x10, 1)
num_ent, = struct.unpack('>H', f.read(2))
entries = []
for _ in range(num_ent):
    ent_id, ent_off, ent_len = struct.unpack('>III', f.read(0xC))
    entries.append((ent_id, ent_off, ent_len))

print(entries)
ent_data = {}
for ent_id, ent_off, ent_len in entries:
    f.seek(ent_off)
    ent_data[ent_id] = f.read(ent_len)

data_fork = ent_data.get(1, b'')
if not data_fork:
    # i, = re.findall(r'\.(\d{3})\.', sys.argv[1])
    # print(f'no data fork, found {i}, trying '+re.sub(rf'(.+?)\.{i}', rf'\1.{int(i) - 1:03}', sys.argv[1][:-4]))
    try:
        data_fork = open(sys.argv[2], 'rb').read()
    except (FileNotFoundError, IndexError):
        pass

rsrc_fork = ent_data.get(2, b'')
file_name = ent_data.get(3, b'')
# if not file_name:
#     file_name_len = rsrc_fork[0x30]
#     file_name = rsrc_fork[0x31:0x31 + file_name_len]

if not file_name:
    file_name = os.path.basename(sys.argv[1]).replace('.rsrc', '')
    file_name = re.sub(r'^\._', '', file_name)
    file_name = parse.unquote_to_bytes(file_name)
    try:
        if japanese:
            file_name = file_name.decode('utf-8').encode('shift-jis')
        else:
            file_name = file_name.decode('utf-8').encode('mac-roman')
    except UnicodeDecodeError:
        pass

try:
    crtime, modtime = struct.unpack('>ii8x', ent_data.get(8))
    crtime += 3029529600  # AppleDouble is seconds from 2000-01-01, need to convert to HFS
    modtime += 3029529600
except TypeError:
    # crtime, modtime = 0, 0
    statinfo = os.stat(sys.argv[1])
    crtime = int(statinfo.st_ctime) + 2082844800
    modtime = int(statinfo.st_mtime) + 2082844800

if 9 in ent_data:
    ftype, fcreator, fflags = struct.unpack('>4s4sH', ent_data.get(9)[:10])
else:
    ftype, fcreator, fflags = (b'XXXX', b'XXXX', 0)

if japanese:
    print(file_name.decode("shift-jis"), len(data_fork), len(rsrc_fork), crtime, modtime, ftype, fcreator, fflags)
else:
    print(file_name.decode("macroman"), len(data_fork), len(rsrc_fork), crtime, modtime, ftype, fcreator, fflags)

if japanese:
    outfile_name = os.path.join(os.path.dirname(sys.argv[1]), f'{file_name.decode("shift-jis")}.bin')
else:
    outfile_name = os.path.join(os.path.dirname(sys.argv[1]), f'{file_name.decode("macroman")}.bin')

if not rsrc_fork:
    with open(outfile_name, 'wb') as f:
        f.write(file_to_macbin(len(data_fork), 0, crtime, (modtime if modtime > 0 else 0), ftype, fcreator, fflags, file_name))
        f.write(data_fork)
else:
    with open(outfile_name, 'wb') as f:
        f.write(file_to_macbin(len(data_fork), len(rsrc_fork), crtime, (modtime if modtime > 0 else 0), ftype, fcreator, fflags, file_name))
        if data_fork:
            f.write(data_fork)
            f.write(b'\x00' * (-len(data_fork) % 128))
        if rsrc_fork:
            f.write(rsrc_fork)
            f.write(b'\x00' * (-len(rsrc_fork) % 128))

os.utime(outfile_name, (modtime - 2082844800, modtime - 2082844800))
