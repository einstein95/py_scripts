from glob import glob
from shutil import move
from struct import unpack

files = glob("*.uni")
files.sort()
for i, fn in enumerate(files):
    with open(fn, "rb") as f:
        f.seek(0x132)
        namelen = unpack("<H", f.read(2))[0]
        name = f.read(namelen).decode()
    move(fn, f"{i+1:02}. {name}.uni")
