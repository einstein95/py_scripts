import struct
from sys import argv

with open(argv[1], "rb") as f:
    f.seek(-4, 2)
    size = struct.unpack("I", f.read(4))[0]
    f.seek(-(size + 8), 2)
    data = f.read(size)
    with open(argv[1].replace(".exe", ".swf"), "wb") as o:
        o.write(data)
