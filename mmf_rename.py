# Renames music files ripped using offzip from MMF games
from os import unlink
from sys import argv

with open(argv[1], "rb") as f:
    chunks = []
    while True:
        buf = f.read(4)
        if not buf:
            break
        null_pos = buf.find(b"\x00")
        if null_pos != -1:
            chunks.append(buf[:null_pos])
            break
        chunks.append(buf)

    name = b"".join(chunks)
    if not name.isascii():
        exit(1)
    name = name.decode()
    data = f.read()

print(argv[1], "->", name)
with open(name, "wb") as f:
    f.write(data)

unlink(argv[1])
