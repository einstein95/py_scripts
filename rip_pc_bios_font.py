from sys import argv

with open(argv[1], "rb") as f:
    fsize: int = f.seek(0, 2)
    for i in range(0, fsize, 0x2000):
        f.seek(i + 0x1A6E)
        font: bytes = f.read(0x400)
        if len(font) < 0x400:
            font = b"\x00" * 0x100 + font[:0x300]
        font += b"\x00" * 0x400
        with open(f"{argv[1]}_{i:08x}.bin", "wb") as of:
            of.write(font)
