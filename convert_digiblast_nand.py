from pathlib import Path
from sys import argv

BASE_OFFSET = 0x17B800
fn = Path(argv[1])
with open(fn, "rb") as f:
    fsize = f.seek(0, 2)
    fsize -= BASE_OFFSET
    f.seek(BASE_OFFSET)
    o = []
    for i in range(fsize // 0x210):
        o.append(f.read(0x200))
        f.seek(0x10, 1)

o = b"".join(o)
assert o[:4] == b"hsqs"
fn.with_suffix(".squashfs").write_bytes(o)
