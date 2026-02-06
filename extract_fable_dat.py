from struct import unpack
from sys import argv

with open(argv[1], "rb") as f:
    assert f.read(4) == b"ARC1"
    num_files = unpack("<H", f.read(2))[0]
    for _ in range(num_files):
        name = f.read(14).split(b"\0", 1)[0].decode("ascii")
        offset, size = unpack("<II", f.read(8))
        tmp = f.tell()
        f.seek(offset)
        data = f.read(size)
        f.seek(tmp)
        with open(f"extracted/{name}", "wb") as out:
            out.write(data)
