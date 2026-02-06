import zipfile
from io import BytesIO, FileIO
from pathlib import Path, PureWindowsPath
from struct import unpack
from sys import argv

p = Path(argv[1])
z = zipfile.ZipFile(p)
f = BytesIO(z.read(p.name))

unk1, unk2, numFiles = unpack("<III", f.read(0xC))
print(f"{unk1=}, {unk2=}, {numFiles=}")
with open(p.with_suffix(".md5"), "w") as of:
    for _ in range(numFiles):
        filename, hash = unpack("1024s32s", f.read(0x420))
        fn = PureWindowsPath(filename.decode().rstrip("\x00"))
        of.write(f"{hash.decode()}  {fn.as_posix()}\n")
