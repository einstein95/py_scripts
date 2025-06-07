#!/usr/bin/python
import pathlib
from glob import glob
from sys import argv

# jp = cp932
# eu = cp1252
target_encoding = argv[1]
all_files = [pathlib.Path(file) for file in glob("**/*", recursive=True)]
all_files = [file for file in all_files if file.is_file()]
for file in all_files:
    try:
        new_file_name = pathlib.PureWindowsPath(
            str(file).replace("/", "\\").encode("latin1").decode(target_encoding)
        )
    except UnicodeEncodeError:
        continue
    pathlib.Path(new_file_name.parent.as_posix()).mkdir(parents=True, exist_ok=True)
    file.rename(new_file_name.as_posix())
