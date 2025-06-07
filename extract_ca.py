import sys
from struct import unpack

ARCHIVE_MAGIC = b"binary.archive00"
HEADER_SIZE = 16
ENTRY_SIZE = 64
ENTRY_STRUCT = "<16s4sii36x"


def read_header(f):
    header = f.read(HEADER_SIZE)
    if header != ARCHIVE_MAGIC:
        raise ValueError("Invalid file format")
    f.seek(8, 1)  # skip null
    directory_offset = unpack("<I", f.read(4))[0]
    return directory_offset


def read_directory(f, directory_offset):
    f.seek(directory_offset)
    directory = []
    while True:
        entry = f.read(ENTRY_SIZE)
        if not entry or len(entry) < ENTRY_SIZE:
            break
        filename, filetype, filelength, fileoffset = unpack(ENTRY_STRUCT, entry)
        filename = filename.decode("utf-8").rstrip("\x00")
        filetype = filetype[::-1].decode("utf-8").rstrip("\x00")
        directory.append((filename, filetype, filelength, fileoffset))
    return directory


def extract_files(f, directory):
    for filename, filetype, filelength, fileoffset in directory:
        print(f"Extracting {filename} ({filetype})")
        f.seek(fileoffset)
        data = f.read(filelength)
        with open(filename, "wb") as out:
            out.write(data)


def main(archive_path):
    with open(archive_path, "rb") as f:
        directory_offset = read_header(f)
        directory = read_directory(f, directory_offset)
        for filename, filetype, filelength, fileoffset in directory:
            print(filename, filetype, filelength, fileoffset)
        extract_files(f, directory)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <archive_file>")
        sys.exit(1)
    try:
        main(sys.argv[1])
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
