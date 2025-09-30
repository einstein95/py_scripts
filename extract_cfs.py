from struct import unpack
from sys import argv


class file_reader:
    def __init__(self, filename):
        self.file = open(filename, "rb")

    def seek(self, offset, whence=0):
        self.file.seek(offset, whence)

    def read(self, length):
        return self.file.read(length)

    def read_string(self, length):
        string = self.file.read(length)
        return string.decode("utf-8").strip("\x00")

    def read_stringz(self):
        string = b""
        while True:
            char = self.file.read(1)
            if char == b"\x00":
                break
            string += char
        return string.decode("utf-8")

    def read_uint32(self):
        return unpack("<I", self.file.read(4))[0]


# Extracts Compound File System (CFS) files from the game "Chaos Island: The Lost World - Jurassic Park" (1997)
f = file_reader(argv[1])
assert f.read(4) == b"FSH2"
header_length = f.read_uint32()
assert header_length == 0x1D
number_files = f.read_uint32()
f.seek(header_length - 4, 1)
# This puts the file pointer at the end of the header
files = []
for _ in range(number_files):
    # File header format:
    # 0x00: 4 bytes - file name length + 9
    # 0x04: 4 bytes - unknown (always 0x02?)
    # 0x08: 4 bytes - offset
    # 0x0C: 4 bytes - file name
    file_name_length = f.read_uint32()
    unknown2 = f.read_uint32()
    file_offset = f.read_uint32()
    # file_name = f.read_stringz()
    file_name = f.read_string(file_name_length - 9 + 1)  # +1 for null terminator
    files.append((file_name, file_offset))

# Because they're not sorted for some reason
files = sorted(files, key=lambda x: x[1])

# Now we can read the files
for i, (file_name, file_offset) in enumerate(files):
    if i == len(files) - 1:
        # Last file
        f.seek(0, 2)
        file_length = f.file.tell() - file_offset
    else:
        file_length = files[i + 1][1] - file_offset
    f.seek(file_offset)
    file_header_length = f.read_uint32()
    data_offset = f.read_uint32()
    unknown1 = f.read_uint32()
    unknown2 = f.read_uint32()
    unknown3 = f.read(8)
    f.seek(data_offset)
    file_data = f.read(file_length - file_header_length - 4)
    with open(file_name, "wb") as out_file:
        out_file.write(file_data)
    print(f"Extracted {file_name} ({len(file_data):#x} bytes)")
