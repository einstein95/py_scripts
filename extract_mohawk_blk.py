import struct
import sys


def read_resource_block(blockFile, output_dir, file_type):
    blockFile.seek(2, 1)
    count = struct.unpack("<H", blockFile.read(2))[0]
    blockFile.seek(2, 1)
    type_ = blockFile.read(4)
    assert type_ == b"FLEX", "Invalid block type, expected 'FLEX'"

    for i in range(count):
        if not file_type == "pic":
            offset, unk, size = struct.unpack("<III", blockFile.read(12))
            print(f"Resource {i:03d}: {offset=:08x}, {unk=:08x}, {size=:08x}")
            if unk != 0:
                raise Exception(f"Unexpected unk value: {unk}")
        else:
            offset, unk, _, size, _ = struct.unpack("<I4xHHHH", blockFile.read(16))
            assert unk == size, "Unexpected unk1 value, expected size"
            print(f"Resource {i:03d}: {offset=:08x}, {size=:04x}")
            if size > 0xFFFF0000:
                size &= 0x0000FFFF

        if not offset or not size:
            continue

        current_pos = blockFile.tell()
        blockFile.seek(offset)
        data = blockFile.read(size)
        filename = f"{output_dir}/{i:03d}.bin"
        with open(filename, "wb") as f:
            f.write(data)
        blockFile.seek(current_pos)


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <block_file> <output_dir>")
        return
    block_file_path = sys.argv[1]
    output_dir = sys.argv[2]
    with open(block_file_path, "rb") as blockFile:
        read_resource_block(
            blockFile,
            output_dir,
            "pic" if block_file_path.lower().endswith("pics.blk") else "",
        )


if __name__ == "__main__":
    main()
