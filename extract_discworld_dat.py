from pathlib import Path
from struct import unpack
from sys import argv

fn = Path(argv[1])
base = fn.stem
with open(fn, "rb") as f:
    unknown = unpack("<I", f.read(4))[0]
    print(f"Unknown: {unknown:04x}")
    while True:
        sizedata = f.read(4)
        if not sizedata:
            break
        fs = unpack("<I", sizedata)[0]
        with open(f"{base}-{f.tell():08x}.bin", "wb") as of:
            of.write(f.read(fs))
