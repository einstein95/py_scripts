import re
from hashlib import sha1

table = [i.split('\t') for i in open('l').read().splitlines()]
for file, hash, size in table:
    size = int(size)
    hash = hash.replace('***', '.{20}')
    with open(file, 'rb') as f:
        sha = sha1(f.read()).hexdigest()
        fsize = f.tell()
        if fsize != size:
            print(f'{file}: Size mismatch ({fsize} != expected {size})')
            continue
        if not re.search(hash, sha):
            print(f'{file}: SHA-1 mismatch ({sha} != expected {hash})')
            continue
        print(f'{file}: Ok ({sha}, {size})')
