from struct import unpack
from sys import argv

search_sig = b"FORM\x00\x00\x00\x0eXDIR"
f = open(argv[1], "rb").read()
num = 1
while True:
    try:
        offset = f.index(search_sig)
    except ValueError:
        break
    print(offset)
    filesize = unpack(">I", f[offset + 0x1A : offset + 0x1E])[0] + 0x20
    with open(f"{argv[1]}-{num:03}.xmi", "wb") as of:
        of.write(f[offset : offset + filesize])
    f = f[offset + 1 :]
    num += 1
