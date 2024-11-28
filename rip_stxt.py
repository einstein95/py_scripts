# Extract text from STXT Director chunks
from struct import unpack
from sys import argv

files = argv[1:]
for file in files:
    if file.startswith("STXT-"):
        with open(file, "rb") as f:
            f.seek(4)
            tlen = unpack(">I", f.read(4))[0]
            f.seek(12)
            d = f.read(tlen)

        with open(file.replace(".bin", ".txt"), "w") as f:
            f.write(d.decode("mac-roman").replace("\r", "\n"))
    elif file.startswith("XMED-"):
        with open(file, "rb") as f:
            _, _, filelen = unpack('>III', f.read(12))
            d = f.read(filelen)

        with open(file.replace(".bin", ".swf"), "wb") as f:
            f.write(d)