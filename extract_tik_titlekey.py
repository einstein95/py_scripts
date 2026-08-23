from sys import argv

for fn in argv[1:]:
    with open(fn, "rb") as f:
        f.seek(0x180)
        titlekey = f.read(0x10)
        f.seek(0x2A0)
        titleid = f.read(0x10)
        print(f"{titleid.hex()} = {titlekey.hex()}")
