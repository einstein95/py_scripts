import struct
from pathlib import Path, PureWindowsPath


def extract_xfle_files(input_file_path, output_directory):
    """
    Extract files from a DAT file using the XFLE format.

    Args:
        input_file_path (str or Path): Path to the input DAT file
        output_directory (str or Path): Directory where extracted files will be saved
    """
    # Convert to Path objects
    input_path = Path(input_file_path)
    output_path = Path(output_directory)

    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    with input_path.open("rb") as f:
        # Get file size
        f.seek(0, 2)  # Seek to end of file
        dat_size = f.tell()
        f.seek(0)  # Reset to beginning

        offset = 0
        file_count = 0

        while True:

            offset = f.tell()
            if offset >= dat_size:
                break
            # Check for XFLE signature
            signature = f.read(4)
            if signature != b"XFLE":
                print(
                    f"Skipping invalid signature at offset {offset:#04x}: {signature!r}"
                )
                exit(1)

            # Read the rest of the header
            name_bytes = f.read(0x80)  # 128 bytes for name
            data_offset = struct.unpack("<I", f.read(4))[
                0
            ]  # 4 bytes offset (little endian)
            size = struct.unpack("<I", f.read(4))[0]  # 4 bytes size (little endian)
            f.read(4)  # 4 bytes dummy
            f.read(4)  # 4 bytes duplicate size (little endian)

            # print(
            #     f"Header read: name_bytes={name_bytes.lstrip(b"\x00").split(b"\x00")[0]!r}, data_offset={data_offset:#04x}, size={size:#x}"
            # )

            # Process the name - remove null bytes and decode

            try:
                name = PureWindowsPath(
                    name_bytes[1:].split(b"\x00")[0].decode("utf-8").lstrip("\\")[2:]
                )
            except UnicodeDecodeError:
                print(f"Warning: Skipping file with undecodable name: {name_bytes!r}")
                exit(1)

            # If we have a valid name and size, extract the file
            if name and size > 0:
                # Save current position
                current_pos = f.tell()

                # Extract the file data
                f.seek(data_offset)
                file_data = f.read(size)

                # Write to output file using pathlib
                output_file_path = output_path / name
                output_file_path.parent.mkdir(parents=True, exist_ok=True)
                if not output_file_path.exists():
                    output_file_path.write_bytes(file_data)
                else:
                    output_file_path = output_file_path.with_name(
                        output_file_path.name + f"_dup{file_count}"
                    )
                    output_file_path.write_bytes(file_data)

                print(f"Extracted: {name} ({size} bytes)")

                file_count += 1

                if current_pos != data_offset:
                    f.seek(current_pos)

            # Move to next potential header
            # offset += 1

    print(f"Extraction complete. {file_count} files extracted.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python extract_xfle.py <input_file.dat> <output_directory>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_dir = sys.argv[2]

    extract_xfle_files(input_file, output_dir)
