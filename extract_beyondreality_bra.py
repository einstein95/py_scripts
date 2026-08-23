from pathlib import Path, PureWindowsPath
from struct import unpack
from sys import argv
from zlib import decompress

f = open(argv[1], "rb")
assert f.read(4) == b"PDA\x00"
assert unpack("<I", f.read(4))[0] == 2
toc_offset = unpack("<I", f.read(4))[0]
num_toc_entries = unpack("<I", f.read(4))[0]
f.seek(toc_offset)
for i in range(num_toc_entries):
    f.seek(8, 1)  # skip unknown
    file_size, decompressed_size, name_size, file_offset = unpack("<IIH2xI", f.read(16))
    # Read file name until null byte
    file_name = f.read(name_size).split(b"\x00", 1)[0]
    file_name = Path(PureWindowsPath(file_name.decode("utf-8")))
    print(
        f"{file_name}: {file_size} bytes (decompressed: {decompressed_size} bytes) at offset {file_offset}"
    )
    tmp = f.tell()
    f.seek(file_offset)
    dec_size, file_size = unpack("<II8x", f.read(16))
    data = f.read(file_size)
    file_name.parent.mkdir(parents=True, exist_ok=True)
    file_name.write_bytes(decompress(data, wbits=-15))
    f.seek(tmp)
    print(hex(tmp))
