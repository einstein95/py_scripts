import argparse
import os
from pathlib import Path
from struct import unpack

"""
Extract files from a Q2Data WAD archive. (Conquest of the New World)
Usage:
    python extract_wad.py <wad_file> [-o <output_dir>]
"""


def extract_wad(filename, output_dir):
    files = []
    with open(filename, "rb") as file:
        _, num_files = unpack("<IB", file.read(5))
        print(f"Number of files: {num_files}")
        for i in range(num_files):
            offset, size = unpack("<II", file.read(8))
            name_bytes = []
            while True:
                c = file.read(1)
                if c == b"\0":
                    break
                name_bytes.append(c)
            name = b"".join(name_bytes).decode("ascii")
            print(f"File {i}: {name} (offset: {offset}, size: {size})")
            files.append((name, offset, size))

        for name, offset, size in files:
            file.seek(offset)
            data = file.read(size)
            with open(output_dir / name, "wb") as f:
                f.write(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract files from a WAD archive.")
    parser.add_argument("wad_file", help="Path to the WAD file", type=Path)
    parser.add_argument(
        "-o", "--output", help="Output directory", default=None, type=Path
    )
    args = parser.parse_args()

    wad_path = args.wad_file
    output_dir = args.output if args.output else Path(wad_path.stem)
    os.makedirs(output_dir, exist_ok=True)
    extract_wad(wad_path, output_dir)
