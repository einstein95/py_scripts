#!/usr/bin/env python3
from pathlib import Path
from struct import unpack
from sys import argv


def main():
    if len(argv) < 2:
        print("Usage: python extract.py <NexusTK.dat> [output_dir]")
        exit(1)

    input_path = argv[1]
    output_dir = Path(argv[2]) if len(argv) > 2 else Path("extracted")

    with open(input_path, "rb") as f:
        # Read metadata
        num_files = (
            unpack("<I", f.read(4))[0] - 1
        )  # last entry has the offset set to the file size
        toc = []
        for _ in range(num_files):
            toc.append(unpack("<I13s", f.read(17)))

        print(f"Found {num_files} files in archive")

        # Create output directory
        output_dir.mkdir(exist_ok=True)

        # Get file size for last file calculation
        f.seek(0, 2)
        file_size = f.tell()

        # Extract files
        for i in range(num_files):
            start, file_name = toc[i]
            file_name = file_name.split(b"\x00")[0].decode()
            size = (toc[i + 1][0] if i < num_files - 1 else file_size) - start

            # Read file data
            f.seek(start)
            data = f.read(size)

            # Determine extension and write file
            output_file = output_dir / file_name
            output_file.write_bytes(data)

            print(f"{output_file.name} ({size:,})")

    print(f"\nExtraction complete! {num_files} files extracted to '{output_dir}'")


if __name__ == "__main__":
    main()
