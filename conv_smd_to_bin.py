import sys

f = open(sys.argv[1], "rb")
fsize = f.seek(0, 2)
f.seek(0x200)
num_banks = (fsize - 0x200) // 0x4000
print(f"Number of banks: {num_banks}")
output = bytearray()
for i in range(num_banks):
    f.seek(0x200 + i * 0x4000)
    odd_bytes = f.read(0x2000)
    even_bytes = f.read(0x2000)
    for j in range(0x2000):
        output.append(even_bytes[j])
        output.append(odd_bytes[j])

with open(sys.argv[2], "wb") as out:
    out.write(output)
