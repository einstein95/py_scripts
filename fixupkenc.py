#!/usr/bin/python
from shutil import move
from glob import glob
from sys import argv
from pathlib import Path

# jp = cp932
# eu = cp1252
encoding = argv[1]
files = [Path(i) for i in glob('**/*', recursive=True)]
files = [i for i in files if i.is_file()]

for file in files:
    of = b""
    for i in file:
        if ord(i) > 0xDC00:
            of += bytes([ord(i) - 0xDC00])
        else:
            of += i.encode("utf8")
    of = of.replace(b"/", b"\\")
    newfilename = of.decode(encoding)
    move(file, newfilename)
