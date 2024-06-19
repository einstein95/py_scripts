#!/usr/bin/python3
from struct import unpack
from sys import argv
from os.path import splitext

f = open(argv[1], "rb")
(dname,) = unpack("65p", f.read(65))
print(dname.decode("mac-roman"))
f.seek(0x40)
(dsklen,) = unpack(">I", f.read(4))
f.seek(0x54)
with open(splitext(argv[1])[0] + ".dsk", "wb") as of:
    of.write(f.read(dsklen))
