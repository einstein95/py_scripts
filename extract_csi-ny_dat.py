from io import BytesIO
from struct import unpack
import sys
import zlib


f = open(sys.argv[1], "rb")
magic1 = f.read(4)
magic2 = f.read(4)
if magic1 != b"GRF\x05":
    raise ValueError("Incorrect magic1 value")
if magic2 == b"GRF\x01":
    endian = "<"
elif magic2 == b"\x01FRG":
    endian = ">"
else:
    raise ValueError("Incorrect magic2 value")
toc_offset = unpack(f"{endian}I", f.read(4))[0]

f.seek(toc_offset)
d = f.read()
d_ = zlib.decompress(d)
open("debug.dat", "wb").write(d_)
toc = BytesIO(d_)

if endian == ">":
    toc.seek(11)
else:
    toc.seek(6)
while True:
    if endian == ">":
        toc.seek(15, 1)
    else:
        toc.seek(9, 1)
    slen = toc.read(1)[0]
    fn = toc.read(slen).decode()
    offset, flen = unpack(f"{endian}II", toc.read(8))
    toc.seek(1, 1)
    print(f"{offset:#08x}\t{flen:<#8x}\t{fn}")
    f.seek(offset)
    with open("out/" + fn, "wb") as of:
        of.write(zlib.decompress(f.read(flen)))
    if toc.read(1) == b"":
        break
