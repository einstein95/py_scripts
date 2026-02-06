from struct import unpack
from sys import argv

f = open(argv[1], "rb")
assert f.read(4) == b"FLDF"
version = f.read(4).decode()
header_len, num_files = unpack("<II", f.read(8))
f.seek(header_len)
for _ in range(num_files):
    fname, offset, size = unpack("<12sII", f.read(20))
    print(fname, offset, size)
    tmp = f.tell()
    f.seek(offset)
    with open(fname.split(b"\x00", 1)[0].decode(), "wb") as of:
        of.write(f.read(size))

    f.seek(tmp)
