from sys import argv


f = open(argv[1], "rb")
f.seek(-2, 2)
num_files = int.from_bytes(f.read(2), "little")
f.seek(num_files * -0x15 - 2, 2)
for _ in range(num_files):
    size = int.from_bytes(f.read(4), "little")
    offset = int.from_bytes(f.read(4), "little")
    filename = f.read(13).split(b"\x00", 1)[0].decode("ascii")
    cur = f.tell()
    f.seek(offset)
    with open(f"extracted/{filename}", "wb") as of:
        of.write(f.read(size))
    f.seek(cur)
