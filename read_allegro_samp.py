import os
import struct
from sys import argv

base, _ = os.path.splitext(argv[1])

with open(argv[1], "rb") as f:
    if f.read(4) != b"SAMP":
        raise ValueError("Not a SAMP file")
    f.seek(8, 1)
    bits, freq, length = struct.unpack_from(">hHl", f.read(8))
    channels = 1 + (bits < 0)
    bits = abs(bits)
    data = f.read(length * channels * (bits // 8))

print(f"{argv[1]}: PCM{bits}{'LE' if bits > 8 else ''}_U {channels} {freq} {length}")
open(base + ".pcm", "wb").write(data)
