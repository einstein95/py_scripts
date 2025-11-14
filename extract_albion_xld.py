from struct import unpack
from sys import argv

f = open(argv[1], "rb")
assert f.read(6) == b"XLD0I\0", "Invalid XLD file"
numfiles = unpack("<H", f.read(2))[0]
filesizes = unpack("<" + "I" * numfiles, f.read(numfiles * 4))
for i, fs in enumerate(filesizes):
    with open(argv[1][:-4] + f"_{i:04x}.bin", "wb") as of:
        of.write(f.read(fs))
