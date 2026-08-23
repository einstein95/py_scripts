from struct import unpack
from sys import argv

with open(argv[1], "rb") as f:
    f.seek(0x84)
    cwav_offset = unpack("<I", f.read(4))[0]
    f.seek(cwav_offset + 0xC)
    cwav_size = unpack("<I", f.read(4))[0]
    f.seek(cwav_offset)
    cwav_data = f.read(cwav_size)

with open(argv[1] + ".bcwav", "wb") as f:
    f.write(cwav_data)
