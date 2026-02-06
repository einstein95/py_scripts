#!/usr/bin/env python3
from pathlib import Path
from struct import Struct
from sys import argv

from lzss import decompress  # type: ignore

# Pre-compile struct formats for better performance
HEADER_STRUCT = Struct("<H")
TOC_ENTRY_STRUCT = Struct("<13sI")
MAGIC_SIZE_STRUCT = Struct("<4sI")


def main():
    if len(argv) < 2:
        print("Usage: python extract.py <axia.dat> [output_dir]")
        exit(1)

    input_path = argv[1]
    output_dir = Path(argv[2]) if len(argv) > 2 else Path("extracted")

    with open(input_path, "rb") as f:
        # Validate header
        if f.read(4) != b"LIB\x1a":
            raise ValueError("Invalid LIB file")

        # Read number of files
        num_files = HEADER_STRUCT.unpack(f.read(2))[0]

        # Read entire TOC at once instead of per-file
        toc_data = f.read(17 * num_files)
        file_toc = [
            (
                TOC_ENTRY_STRUCT.unpack(toc_data[i * 17 : (i + 1) * 17])[0]
                .rstrip(b"\0")
                .decode(),
                TOC_ENTRY_STRUCT.unpack(toc_data[i * 17 : (i + 1) * 17])[1],
            )
            for i in range(num_files)
        ]

        print(f"Found {num_files} files in archive")
        output_dir.mkdir(exist_ok=True)

        # Get file size once
        f.seek(0, 2)
        file_size = f.tell()

        # Process files
        for i, (name, offset) in enumerate(file_toc):
            next_offset = file_toc[i + 1][1] if i < num_files - 1 else file_size
            size = next_offset - offset

            # Read file data
            f.seek(offset)
            data = f.read(size)

            # Check compression
            is_compressed = False
            if len(data) >= 8:
                magic, decompressed_size = MAGIC_SIZE_STRUCT.unpack(data[:8])
                if magic == b"LZV\x1a":
                    is_compressed = True
                    data = decompress(data[8:])
                    if len(data) != decompressed_size:
                        raise ValueError(f"Decompression failed for {name}")

            # Write file
            (output_dir / name).write_bytes(data)

            print(
                f"{name} ({size:,} bytes, {'un' if not is_compressed else ''}compressed)"
            )

    print(f"\nExtraction complete! {num_files} files extracted to '{output_dir}'")


if __name__ == "__main__":
    main()
