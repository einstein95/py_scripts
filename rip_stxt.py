# Extract text from STXT Director chunks
from os import path
from struct import unpack
from sys import argv

files = argv[1:]
for file in files:
    fn = path.basename(file)
    print(f"Processing {file}...")
    if "STXT-" in fn:
        with open(file, "rb") as f:
            filesize = f.seek(0, 2)
            f.seek(0)
            if filesize < 20:
                print(f"File {file} is too small to be a valid STXT file.")
                continue
            f.seek(4)
            tlen = unpack(">I", f.read(4))[0]
            f.seek(0xC)
            d = f.read(tlen)

        outfn = file.replace(".bin", ".txt")
        print(f"Writing {outfn}...")
        with open(outfn, "wb") as f:
            f.write(d)

    elif "XMED-" in fn:
        with open(file, "rb") as f:
            _, _, filelen = unpack(">III", f.read(12))
            d = f.read(filelen)

        with open(file.replace(".bin", ".swf"), "wb") as f:
            f.write(d)
