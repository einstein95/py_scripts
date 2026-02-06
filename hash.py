# Checksum ROM files and print their size, crc32, md5, sha1, and sha256 hashes.

import hashlib
import sys
import zlib


def sha1sum(data):
    sha1 = hashlib.sha1()
    sha1.update(data)
    return sha1.hexdigest()


def sha256sum(data):
    sha256 = hashlib.sha256()
    sha256.update(data)
    return sha256.hexdigest()


def md5sum(data):
    md5 = hashlib.md5()
    md5.update(data)
    return md5.hexdigest()


def crc32sum(data):
    return f"{zlib.crc32(data) & 0xFFFFFFFF:08x}"


def human_readable_size(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            if size == int(size):
                return f"{int(size)}{unit}"
            return f"{size:.2f}{unit}"
        size /= 1024
    if size == int(size):
        return f"{int(size)}TB"
    return f"{size:.2f}TB"


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 hash.py <path_to_file>")
        sys.exit(1)

    for file_path in sys.argv[1:]:
        with open(file_path, "rb") as f:
            rom_data = f.read()

        print(
            f"{file_path}: size:{human_readable_size(len(rom_data))} crc32:{crc32sum(rom_data)} md5:{md5sum(rom_data)} sha1:{sha1sum(rom_data)} sha256:{sha256sum(rom_data)}"
        )


if __name__ == "__main__":
    main()
