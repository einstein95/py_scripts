import os
import re
from hashlib import sha1
from sys import argv

if len(argv) != 2:
    print("Usage: python steamdb_hash.py <file_list>")
    exit(1)

with open(argv[1]) as f:
    table = [i.split("\t") for i in f.read().splitlines()]

for file, hash, size in table:
    if not size:
        # Directory, skip
        continue
    size_int = int(size)
    hash = hash.strip().replace("***", ".{20}")
    file = file.strip()
    if not os.path.isfile(file):
        print(f"{file}: File not found")
        continue
    with open(file, "rb") as f:
        sha = sha1(f.read()).hexdigest()
        fsize = f.tell()
        if fsize != size_int:
            print(f"{file}: Size mismatch ({fsize} != expected {size_int})")
            continue
        if not re.search(hash, sha):
            print(f"{file}: SHA-1 mismatch ({sha} != expected {hash})")
            continue
        print(f"{file}: OK ({sha}, {size})")
