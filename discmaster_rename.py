import shutil
from sys import argv

import requests
from blake3 import blake3

files = argv[1:]
if not files:
    print("Usage: discmaster_rename.py <file1> <file2> ...")
    exit(1)

for f in files:
    with open(f, "rb") as file:
        b = blake3(file.read()).hexdigest()
    r = requests.get(
        f"https://discmaster.textfiles.com/search?b3sum={b}&outputAs=json"
    ).json()
    filenames = [i["filename"] for i in r]
    filename = max(set(filenames), key=filenames.count)
    shutil.move(f, filename)
