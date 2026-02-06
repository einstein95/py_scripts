from pathlib import Path
from struct import unpack
from sys import argv

# pip install lzss
# https://pypi.org/project/lzss/
from lzss import decompress  # type: ignore


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
    return ".bin"


def main():
    if len(argv) < 2:
        print("Usage: python extract.py <axia.dat> [output_dir]")
        exit(1)

    input_path = argv[1]
    output_dir = Path(argv[2]) if len(argv) > 2 else Path("extracted")

    with open(input_path, "rb") as f:
        num_files = unpack("<I", f.read(4))[0]
        f.read(2)
        file_offsets = unpack(f"<{num_files}I", f.read(num_files * 4))
        print(f"Found {num_files} files in archive")
        output_dir.mkdir(exist_ok=True)
        f.seek(0, 2)
        file_size = f.tell()
        for i in range(num_files):
            offset = file_offsets[i]

            # Check if uncompressed flag is set
            is_uncompressed = offset & 0x40000000
            offset &= 0x3FFFFFFF  # Mask off compression flag
            start = offset + 4  # +4 to strip decompressed size
            next_offset = (
                file_offsets[i + 1] & 0x3FFFFFFF if i < num_files - 1 else file_size
            )
            size = next_offset - start

            # Read file data
            f.seek(start)
            data = f.read(size)

            # Decompress if needed
            if not is_uncompressed:
                data = decompress(data)

            # Determine extension and write file
            output_file = output_dir / f"file_{i:04d}{detect_extension(data)}"
            output_file.write_bytes(data)

            comp_status = ("un" if is_uncompressed else "") + "compressed"
            print(f"{output_file.name} ({size:,} bytes, {comp_status})")

    print(f"\nExtraction complete! {num_files} files extracted to '{output_dir}'")


if __name__ == "__main__":
    main()
