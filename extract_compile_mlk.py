from struct import unpack
from sys import argv

f = open(argv[1], "rb")
num_files = f.read(1)[0]
for _ in range(num_files):
    unk, offset, size = unpack("<?II", f.read(9))
    tmp = f.tell()
    f.seek(offset)
    with open(f"{offset:08X}.bin", "wb") as of:
        of.write(f.read(size))

    f.seek(tmp)
