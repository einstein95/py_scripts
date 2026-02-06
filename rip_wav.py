from struct import unpack
from sys import argv

search_sig = b"RIFF"
f = open(argv[1], "rb").read()
num = 1
while True:
    try:
        offset = f.index(search_sig)
    except ValueError:
        break
    print(offset)
    filesize = unpack("<I", f[offset + 4 : offset + 8])[0] + 8
    with open(f"{argv[1]}-{num:03}.wav", "wb") as of:
        of.write(f[offset : offset + filesize])
    f = f[offset + 1 :]
    num += 1
