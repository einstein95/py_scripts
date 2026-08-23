import os
import struct


def extract_archive(archive_path, output_dir="extracted"):
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    with open(archive_path, "rb") as f:
        # Read header (16 bytes)
        header = f.read(16)
        if len(header) < 16:
            raise ValueError("Invalid archive: header too short")

        # Parse header (all little-endian uint32)
        version, toc_offset, unknown, toc_len = struct.unpack("<IIII", header)

        # Verify unknown field matches ToC offset
        if unknown != toc_offset:
            print(
                f"Warning: unknown field ({unknown}) doesn't match ToC offset ({toc_offset})"
            )

        file_offsets = {}
        for _ in range((toc_offset - 0x10) // 8):
            offset, size = struct.unpack("<II", f.read(8))
            if size == offset == 0:
                break
            file_offsets[size] = offset

        # Seek to ToC
        f.seek(toc_offset)
        entry_size = 0x110

        # Parse number of files
        num_files = struct.unpack("<I", f.read(4))[0]
        f.seek(entry_size, 1)
        assert f.tell() == 0x211C

        # Process each file entry
        for i in range(num_files):
            toc_data = f.read(entry_size)
            tmp = f.tell()
            # Parse entry
            file_num, file_name, file_size, unknown_field = struct.unpack(
                "<I260sII", toc_data
            )
            # file_name = file_name.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")
            file_name = (
                file_name.split(b"\x00")[1]
                .decode("utf-8", errors="replace")
                .split("\\")[-1]
            )
            file_offset = file_offsets.get(file_size, 0)  # Default to 0 if not found
            print(
                f'Entry {i}: num={file_num}, name="{file_name}", offset={file_offset}, size={file_size}, unknown={unknown_field:#08x}'
            )

            # Seek to file data
            f.seek(file_offset)

            file_data = f.read(file_size)

            # Write file to output directory
            output_path = os.path.join(output_dir, file_name)
            with open(output_path, "wb") as out_file:
                out_file.write(file_data)

            print(f"Extracted: {file_name} (#{file_num}) at offset {file_offset:#010x}")
            f.seek(tmp)  # Return to next ToC entry

    print(f"Extraction complete. Files saved to: {output_dir}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python extract_archive.py <archive_file>")
        sys.exit(1)

    archive_file = sys.argv[1]
    extract_archive(archive_file)
