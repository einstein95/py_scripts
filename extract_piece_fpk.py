from struct import unpack
from sys import argv

SIGNATURE = b"KAPF"  # FPAK in little-endian
FNAME_LEN = 16

f = open(argv[1], "rb")
sig, num_files = unpack("<4sI", f.read(8))
assert sig == SIGNATURE, f"Invalid signature: {sig!r}"
print(num_files)
for _ in range(num_files):
    fname, offset, fsize = unpack("<16sII", f.read(24))
    fname = fname.decode("ascii").rstrip("\x00")
    print(fname, offset, fsize)
    tmp = f.tell()
    f.seek(offset)
    with open(fname, "wb") as of:
        of.write(f.read(fsize))

    f.seek(tmp)
