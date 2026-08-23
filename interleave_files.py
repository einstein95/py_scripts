from itertools import zip_longest
from sys import argv


def interleave(*args):
    return bytearray(x for pair in zip_longest(*args) for x in pair if x is not None)


files: list[bytes] = []
for fn in argv[2:]:
    with open(fn, "rb") as f:
        files.append(f.read())

with open(argv[1], "wb") as f:
    f.write(interleave(*files))
