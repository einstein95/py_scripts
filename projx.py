#!/usr/bin/python3
from struct import unpack
from sys import argv

f = open(argv[1], 'rb')
fn = '.'.join(argv[1].split('.')[:-1])
f.seek(-4, 2)
projoff, = unpack('<I', f.read(4))
f.seek(projoff)
id_, rifxoff = unpack('<4sI', f.read(8))
f.seek(0)
with open(f'{fn}_proj.exe', 'wb') as of:
    of.write(f.read(projoff))

# with open(f'{fn}_unk.bin', 'wb') as of:
#     of.write(f.read(rifxoff - projoff))