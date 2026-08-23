from struct import unpack
from sys import argv

files = argv[1:]
for fn in files:
    f = open(fn, "rb")
    assert f.read(4) == b"MHWK"
    f.seek(4, 1)
    assert f.read(4) == b"WAVE"
    while (tag := f.read(4), taglen := unpack(">I", f.read(4))[0])[0] != b"Data":
        f.seek(taglen, 1)
    f.seek(-8, 1)
    with open(fn + "_cut", "wb") as of:
        of.write(f.read(taglen + 8))
