#!/usr/bin/python3
from os import utime
from sys import argv

f = open(argv[1], 'rb')
f.seek(0x5F)
mod_time = int.from_bytes(f.read(4), 'big') - 2082844800
f.seek(0x41)
print(f'{argv[1]}: removing MacBin header, {f.read(8).decode("mac-roman")}')
f.seek(0x53)
datalen = int.from_bytes(f.read(4), 'big')
f.seek(0x80)
data = f.read(datalen)
f.close()
open(argv[1], 'wb').write(data)
utime(argv[1], (mod_time, mod_time))
