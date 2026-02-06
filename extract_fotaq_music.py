#!/usr/bin/env python3
from pathlib import Path
from struct import unpack
from sys import argv


def detect_extension(data: bytes) -> str:
    """Detect file extension from magic bytes."""
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WAVE":
        return ".wav"
    if data.startswith(b"FORM") and len(data) >= 12 and data[8:12] == b"XDIR":
        return ".xmi"
    if data.startswith(b"UN05"):
        return ".uni"
    if data.startswith(b"Creative Voice File"):
        return ".voc"
    if data.startswith(b"MThd"):
        return ".mid"
    return ".bin"


def main():
    if len(argv) < 2:
        print("Usage: python extract.py <axia.dat> [output_dir]")
        exit(1)

    input_path = argv[1]
    output_dir = Path(argv[2]) if len(argv) > 2 else Path("extracted")

    with open(input_path, "rb") as f:
        # Read metadata
        num_files = unpack("<H", f.read(2))[0]
        offsets = unpack(f"<{num_files*2}H", f.read(num_files * 4))
        file_offsets = []
        for i in range(0, num_files * 2, 2):
            file_offsets.append(offsets[i + 1] << 4 | offsets[i])
        print([hex(i) for i in file_offsets])

        print(f"Found {num_files} files in archive")

        # Create output directory
        output_dir.mkdir(exist_ok=True)

        # Get file size for last file calculation
        f.seek(0, 2)
        file_size = f.tell()

        # Extract files
        for i in range(num_files):
            start = file_offsets[i]
            size = (file_offsets[i + 1] if i < num_files - 1 else file_size) - start

            # Read file data
            f.seek(start)
            data = f.read(size)

            # Determine extension and write file
            output_file = output_dir / f"file_{i:04d}{detect_extension(data)}"
            output_file.write_bytes(data)

            print(f"{output_file.name} ({size:,})")

    print(f"\nExtraction complete! {num_files} files extracted to '{output_dir}'")


if __name__ == "__main__":
    main()
