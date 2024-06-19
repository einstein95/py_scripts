#!/usr/bin/python
from glob import glob
from sys import argv
import pathlib

# jp = cp932
# eu = cp1252
encoding = argv[1]
files = [pathlib.Path(i) for i in glob('**/*', recursive=True)]
files = [i for i in files if i.is_file()]
for i in files:
    try:
        newfilename = pathlib.PureWindowsPath(str(i).replace('/','\\').encode('latin1').decode(encoding))
    except UnicodeEncodeError:
        continue
    pathlib.Path(newfilename.parent.as_posix()).mkdir(parents=True, exist_ok=True)
    i.rename(newfilename.as_posix())
