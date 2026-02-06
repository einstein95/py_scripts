# Parse iNES header and print sha1sum of PRG and CHR ROMs

import hashlib
import os
import sys
import zlib


def parse_ines_header(rom_data):
    if rom_data[0:4] != b"NES\x1a":
        raise ValueError("Not a valid iNES file")

    prg_size = rom_data[4] * 16384  # PRG ROM size in bytes
    chr_size = rom_data[5] * 8192  # CHR ROM size in bytes

    has_trainer = rom_data[6] & 0x04
    trainer_size = 512 if has_trainer else 0

    prg_start = 16 + trainer_size
    prg_end = prg_start + prg_size
    chr_start = prg_end
    chr_end = chr_start + chr_size

    prg_rom = rom_data[prg_start:prg_end]
    chr_rom = rom_data[chr_start:chr_end] if chr_size > 0 else b""

    return prg_rom, chr_rom


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
        print("Usage: python3 nes_hash.py <path_to_ines_file>")
        sys.exit(1)

    for ines_file_path in sys.argv[1:]:
        with open(ines_file_path, "rb") as f:
            rom_data = f.read()

        try:
            prg_rom, chr_rom = parse_ines_header(rom_data)
        except ValueError as e:
            print(e)
            sys.exit(1)

        # base_name = os.path.splitext(ines_file_path)[0]
        # with open(base_name + ".prg", "wb") as f:
        #     f.write(prg_rom)
        # if chr_rom:
        #     with open(base_name + ".chr", "wb") as f:
        #         f.write(chr_rom)

        print(f"{ines_file_path}:")
        print(
            f"PRG size:{human_readable_size(len(prg_rom))} crc32:{crc32sum(prg_rom)} md5:{md5sum(prg_rom)} sha1:{sha1sum(prg_rom)} sha256:{sha256sum(prg_rom)}"
        )
        if chr_rom:
            print(
                f"CHR size:{human_readable_size(len(chr_rom))} crc32:{crc32sum(chr_rom)} md5:{md5sum(chr_rom)} sha1:{sha1sum(chr_rom)} sha256:{sha256sum(chr_rom)}"
            )
        if len(sys.argv) > 2:
            print()  # Add a blank line between multiple files


if __name__ == "__main__":
    main()
