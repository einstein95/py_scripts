from struct import unpack
from sys import argv

f = open(argv[1], "rb")
num_files = unpack("<H", f.read(2))[0]
signature = f.read(6)
filever = f.read(8)
assert (
    signature == b"FILPAC"
), f"Expected FILPAC, got {signature.decode()} {filever.decode()}"
print(f"{signature.decode()} {filever.decode()}")
for _ in range(num_files):
    filename = f.read(12).decode("ascii").split("\x00")[0]
    fsize_hi, fsize_lo, offset_hi, offset_lo = unpack("<HHHH", f.read(8))
    f.seek(12, 1)
    fsize = fsize_hi << 16 | fsize_lo
    offset = offset_hi << 16 | offset_lo
    tmp = f.tell()
    f.seek(offset)
    with open("extracted/" + filename, "wb") as of:
        of.write(f.read(fsize))

    f.seek(tmp)
