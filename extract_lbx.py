import sys
from pathlib import Path
from struct import error, unpack


def extract_lbx(lbx_path, output_dir):
    with open(lbx_path, "rb") as f:
        num_files = unpack("<H", f.read(2))[0]
        print(f"Number of files: {num_files}")

        if f.read(2) != b"\xad\xfe":
            raise ValueError("Invalid LBX magic number.")

        f.seek(4, 1)  # skip 4 bytes

        file_offsets = [unpack("<I", f.read(4))[0] for _ in range(num_files + 1)]

        file_names = []
        num_file_offsets = (file_offsets[0] - 0x200) // 32
        print(len(file_names), len(file_offsets) - 1)
        if num_file_offsets > 0:
            f.seek(0x200)
            for _ in range(num_file_offsets):
                name = f.read(9).decode("ascii").rstrip("\x00").replace("\x00", ".")
                comment = f.read(23).decode("ascii").rstrip("\x00")
                print(f"{name=} {comment=}")
                if comment:
                    name = f"{name}_{comment}"
                file_names.append(name)

        file_names += [""] * (num_files - num_file_offsets)
        for i, (name, offset) in enumerate(zip(file_names, file_offsets)):
            if name == "":
                name = f"{offset:08x}.bin"
            f.seek(offset)
            file_size = file_offsets[i + 1] - offset
            header = f.peek(0x10)[:0x10]
            try:
                magic, version = unpack("<HH", header[:4])
                if magic == 0xDEAF and version in (1, 2):
                    f.seek(0x10, 1)
                    file_size -= 0x10
                # else:
                #     print(f"{magic=}, {version=}")
            except error:
                pass
            # file_size = unpack("<I", f.read(4))[0]
            print(f"{offset=:08x} {name=} {file_size=}")
            # f.seek(12, 1)  # skip 12 bytes
            file_data = f.read(file_size)

            out_path = Path(output_dir) / name
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(file_data)
            # print(f"Extracted {name} ({file_size} bytes)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <lbx_file> <output_dir>")
        sys.exit(1)

    extract_lbx(sys.argv[1], sys.argv[2])
