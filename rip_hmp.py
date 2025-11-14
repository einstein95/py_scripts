from sys import argv
from struct import unpack

f = open(argv[1], "rb").read()
num = 1
while True:
    try:
        offset = f.index(b"HMIMIDIP013195" + b"\x00" * 18)
    except ValueError:
        break
    print(offset)
    filesize = unpack("<I", f[offset + 0x20 : offset + 0x24])[0]
    with open(f"{argv[1]}-{num:03}.hmp", "wb") as of:
        of.write(f[offset : offset + filesize])
    f = f[offset + 1 :]
    num += 1
