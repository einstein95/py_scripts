#!/usr/bin/env python3
from sys import argv

offset = int(argv[1], 16)
bank, off = divmod(offset, 0x4000)
print(f"{bank:02X}:{off + 0x4000 if bank > 0 else off:04X}")
