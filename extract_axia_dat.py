#!/usr/bin/env python3
from pathlib import Path
from struct import unpack
from sys import argv


def detect_extension(data: bytes) -> str:
    """Detect file extension from magic bytes."""
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WAVE":
        return ".wav"
    if data.startswith(b"UN05"):
        return ".uni"
    return ".bin"


def main():
    if len(argv) < 2:
        print("Usage: python extract.py <axia.dat> [output_dir]")
        exit(1)

    input_path = argv[1]
    output_dir = Path(argv[2]) if len(argv) > 2 else Path("extracted")

    with open(input_path, "rb") as f:
        # Validate header
        if f.read(8) != b"Axia DAT":
            print("Error: Invalid file format")
            exit(1)

        # Read metadata
        numfiles = unpack("<I", f.read(4))[0]
        file_offsets = unpack(f"<{numfiles}I", f.read(numfiles * 4))

        print(f"Found {numfiles} files in archive")

        # Create output directory
        output_dir.mkdir(exist_ok=True)

        # Get file size for last file calculation
        f.seek(0, 2)
        file_size = f.tell()

        # Extract files
        for i in range(numfiles):
            start = file_offsets[i]
            size = (file_offsets[i + 1] if i < numfiles - 1 else file_size) - start

            # Read file data
            f.seek(start)
            data = f.read(size)

            # Determine extension and write file
            output_file = output_dir / f"file_{i:04d}{detect_extension(data)}"
            output_file.write_bytes(data)

            print(f"{output_file.name} ({size:,})")

    print(f"\nExtraction complete! {numfiles} files extracted to '{output_dir}'")


if __name__ == "__main__":
    main()
