# extract_sx.py
import io
import os
import struct
import sys

import zstandard


# C# DecryptData 方法的 Python 实现
# 这是一个对称的流密码，所以加密和解密是同一个函数
def crypt_data(data, key_lo, key_hi):
    """
    Encrypts or decrypts data using the SakanaGL engine's algorithm.
    This is a direct port of the C# version from GARbro.
    """
    if len(data) < 4:
        return data

    # 模拟 32-bit unsigned integers
    mask = 0xFFFFFFFF

    key_lo = (key_lo ^ 0x159A55E5) & mask
    key_hi = (key_hi ^ 0x075BCD15) & mask

    v1 = (
        key_hi ^ (key_hi << 11) ^ (((key_hi ^ (key_hi << 11)) & mask) >> 8) ^ 0x549139A
    ) & mask
    v2 = (
        v1
        ^ key_lo
        ^ (key_lo << 11)
        ^ (((key_lo ^ (key_lo << 11) ^ (v1 >> 11)) & mask) >> 8)
    ) & mask
    v3 = (v2 ^ (v2 >> 19) ^ 0x8E415C26) & mask
    v4 = (v3 ^ (v3 >> 19) ^ 0x4D9D5BB8) & mask

    # 将字节数据转换为 32-bit little-endian 整数列表
    # C# 的指针转换在 x86/x64 架构上是 little-endian 的
    count = len(data) // 4
    rem = len(data) % 4

    data_u32 = list(struct.unpack_from(f"<{count}I", data))

    for i in range(count):
        t1 = (
            v4 ^ v1 ^ (v1 << 11) ^ (((v1 ^ (v1 << 11) ^ (v4 >> 11)) & mask) >> 8)
        ) & mask
        t2 = (v2 ^ (v2 << 11)) & mask
        v2 = v4
        v4 = (t1 ^ t2 ^ (((t2 ^ (t1 >> 11)) & mask) >> 8)) & mask

        xor_key = ((t1 >> 4) ^ (v4 << 12)) & mask
        data_u32[i] ^= xor_key

        v1 = v3
        v3 = t1

    # 将整数列表转换回字节
    processed_data = bytearray(struct.pack(f"<{count}I", *data_u32))

    if rem > 0:
        processed_data.extend(data[-rem:])

    return processed_data


class SxIndexParser:
    """解析解密解压后的索引数据"""

    def __init__(self, index_data, original_arc_size):
        self.stream = io.BytesIO(index_data)
        self.original_arc_size = original_arc_size
        self.name_list = []
        self.entries = []
        self.arc_info = []
        self.unknown_list = []
        self.tree_data = b""
        self.target_arc_index = -1

    def read_be_u8(self):
        return struct.unpack(">B", self.stream.read(1))[0]

    def read_be_u16(self):
        return struct.unpack(">H", self.stream.read(2))[0]

    def read_be_i32(self):
        return struct.unpack(">i", self.stream.read(4))[0]

    def read_be_u32(self):
        return struct.unpack(">I", self.stream.read(4))[0]

    def read_be_u64(self):
        return struct.unpack(">Q", self.stream.read(8))[0]

    def parse(self):
        self.stream.seek(8)

        name_count = self.read_be_i32()
        for _ in range(name_count):
            length = self.read_be_u8()
            self.name_list.append(self.stream.read(length).decode("utf-8"))

        entry_count = self.read_be_i32()
        for _ in range(entry_count):
            entry = {
                "arc_index": self.read_be_u16(),
                "flags": self.read_be_u16(),
                "offset_div16": self.read_be_u32(),
                "size": self.read_be_u32(),
                "name": "",
                "type": "file",
            }
            entry["offset"] = entry["offset_div16"] * 16
            entry["is_packed"] = (entry["flags"] & 0x03) != 0
            entry["is_encrypted"] = (entry["flags"] & 0x10) == 0
            self.entries.append(entry)

        arc_count = self.read_be_u16()
        for i in range(arc_count):
            info = {
                "field1": self.read_be_u32(),
                "field2": self.read_be_u32(),
                "field3": self.read_be_u32(),
                "size_div16": self.read_be_u32(),
                "field4": self.read_be_u64(),
                "md5": self.stream.read(16),
            }
            self.arc_info.append(info)
            if info["size_div16"] * 16 == self.original_arc_size:
                self.target_arc_index = i

        if self.target_arc_index == -1 and len(self.arc_info) == 1:
            self.target_arc_index = 0

        if self.target_arc_index == -1:
            raise ValueError(
                f"Could not match original archive size {self.original_arc_size} to any archive in index."
            )

        unknown_count = self.read_be_u16()
        for _ in range(unknown_count):
            self.unknown_list.append(self.stream.read(24))

        tree_start_pos = self.stream.tell()
        # BUGFIX: 必须先分配完所有名字，再进行任何过滤
        self._deserialize_tree()
        tree_end_pos = self.stream.tell()
        self.stream.seek(tree_start_pos)
        self.tree_data = self.stream.read(tree_end_pos - tree_start_pos)

        print(
            f"Parsed index: Found {len(self.name_list)} names, {len(self.entries)} total entries."
        )
        print(f"Target archive identified as index {self.target_arc_index}.")

    def _deserialize_tree(self, path=""):
        count = self.read_be_u16()
        name_index = self.read_be_i32()
        file_index = self.read_be_i32()

        name = os.path.join(path, self.name_list[name_index]).replace("\\", "/")

        if file_index == -1:
            for _ in range(count):
                self._deserialize_tree(name)
        else:
            if file_index < len(self.entries):
                self.entries[file_index]["name"] = name


def main():
    if len(sys.argv) != 4:
        print(
            f"Usage: python {sys.argv[0]} <index_file.sx> <game_archive_file> <output_folder>"
        )
        sys.exit(1)

    sx_path = sys.argv[1]
    arc_path = sys.argv[2]
    output_dir = sys.argv[3]

    for path in [sx_path, arc_path]:
        if not os.path.exists(path):
            print(f"Error: Path not found: {path}")
            sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    # --- 1. Parse .sx index ---
    print(f"Parsing index file: {sx_path}...")
    with open(sx_path, "rb") as f:
        signature = f.read(8)
        if signature != b"SSXXDEFL":
            raise ValueError("Invalid .sx file signature.")
        key = struct.unpack(">i", f.read(4))[0]
        f.read(4)
        index_packed_encrypted = f.read()

    length = len(index_packed_encrypted)
    lkey = key + length
    lkey = key ^ (961 * lkey - 124789) ^ 0x2E76034B
    key_lo = lkey & 0xFFFFFFFF
    key_hi = ((lkey >> 32) & 0xFFFFFFFF) ^ 0x2E6
    index_packed = crypt_data(index_packed_encrypted, key_lo, key_hi)

    unpacked_size = struct.unpack(">I", index_packed[:4])[0]
    zctx = zstandard.ZstdDecompressor()
    index_data = zctx.decompress(index_packed[4:], max_output_size=unpacked_size)

    original_arc_size = os.path.getsize(arc_path)
    parser = SxIndexParser(index_data, original_arc_size)
    parser.parse()

    # --- 2. Extract files ---
    print(f"\nExtracting files to: {output_dir}")

    extracted = 0
    skipped = 0
    total = sum(1 for e in parser.entries if e["arc_index"] == parser.target_arc_index)

    with open(arc_path, "rb") as arc:
        for i, entry in enumerate(parser.entries):
            if entry["arc_index"] != parser.target_arc_index:
                skipped += 1
                continue

            name = entry["name"]
            if not name:
                name = f"__unnamed_{i:05d}"

            out_path = os.path.join(output_dir, name)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)

            print(f"  [{extracted + 1}/{total}] {name}")

            arc.seek(entry["offset"])
            packed_data = arc.read(entry["size"])

            if entry["is_encrypted"]:
                key_lo_file = (
                    (entry["offset"] >> 4) ^ (entry["size"] << 16) ^ 0x2E76034B
                ) & 0xFFFFFFFF
                key_hi_file = ((entry["size"] >> 16) ^ 0x2E6) & 0xFFFFFFFF
                packed_data = crypt_data(packed_data, key_lo_file, key_hi_file)

            if entry["is_packed"]:
                u_size = struct.unpack(">I", packed_data[:4])[0]
                file_data = zctx.decompress(packed_data[4:], max_output_size=u_size)
            else:
                file_data = packed_data

            with open(out_path, "wb") as out_file:
                out_file.write(file_data)

            extracted += 1

    print(f"\nDone! Extracted {extracted} file(s) to '{output_dir}'.")
    if skipped:
        print(f"(Skipped {skipped} entries belonging to other archives.)")


if __name__ == "__main__":
    main()
