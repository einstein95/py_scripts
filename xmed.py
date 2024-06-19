import os
from struct import unpack
from sys import argv

with open(argv[1], "rb") as f:
    unk, size = unpack(">4xII", f.read(12))
    print(argv[1], unk, size)
    scheck = f.seek(0, 2) - 12
    f.seek(12)
    assert size == scheck
    with open(argv[1].replace(".bin", "_out.bin"), "wb") as of:
        of.write(f.read(size))
    os.remove(argv[1])
