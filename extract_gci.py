#!/usr/bin/env python3
from sys import argv

with open(argv[1], "rb") as f:
    f.seek(8)
    filename = f.read(32).split(b"\x00")[0].decode()
    f.seek(0x880)
    with open(filename, "wb") as of:
        of.write(f.read())
