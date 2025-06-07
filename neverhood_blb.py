import struct

import dclimplode  # type: ignore


def open_blb_archive(filename):
    entries = []
    ext_data = None

    try:
        with open(filename, "rb") as f:
            # Read header
            header_data = f.read(16)
            if len(header_data) < 16:
                raise Exception("Header too short")
            id1, id2, ext_data_size, file_size, file_count = struct.unpack(
                "<IHHII", header_data
            )
            print(
                f"{id1=:#x}, {id2=:#x}, {ext_data_size=:#x}, {file_size=:#x}, {file_count=}"
            )

            if id1 != 0x2004940 or id2 != 7 or file_size != f.seek(0, 2):
                raise Exception(f"{filename} seems to be corrupt")
            f.seek(16)

            # Load file hashes
            for _ in range(file_count):
                file_hash_bytes = f.read(4)
                if len(file_hash_bytes) < 4:
                    raise Exception("File hash data too short")
                file_hash = struct.unpack("<I", file_hash_bytes)[0]
                entries.append({"fileHash": file_hash})

            ext_data_offsets = []

            # Load file records
            for i in range(file_count):
                record_bytes = f.read(20)
                if len(record_bytes) < 20:
                    raise Exception("File record data too short")
                (
                    type_,
                    compr_type,
                    ext_data_offset,
                    time_stamp,
                    offset,
                    disk_size,
                    size,
                ) = struct.unpack("<BBHIIII", record_bytes)
                entries[i].update(
                    {
                        "type": type_,
                        "comprType": compr_type,
                        # "extData": None,
                        "timeStamp": time_stamp,
                        "offset": offset,
                        "diskSize": disk_size,
                        "size": size,
                    }
                )
                ext_data_offsets.append(ext_data_offset)

            # Load ext data
            # if ext_data_size > 0:
            #     ext_data = f.read(ext_data_size)
            #     for i in range(file_count):
            #         offset = ext_data_offsets[i]
            #         entries[i]["extData"] = (
            #             ext_data[offset - 1 :] if offset > 0 else None
            #         )

        return entries

    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return None


def main():
    for filename in ["A.BLB", "C.BLB", "HD.BLB", "I.BLB", "M.BLB", "S.BLB", "T.BLB"]:
        # filename = "T.BLB"  # Replace with your BLB file
        entries = open_blb_archive(filename)

        f = open(filename, "rb")
        if entries is not None:
            for entry in entries:
                o = dclimplode.decompressobj()
                # print(f"{entry=}")
                f.seek(entry["offset"])
                file_data = f.read(entry["diskSize"])
                if entry["comprType"] == 3:
                    # Decompress the data
                    file_data = o.decompress(file_data)
                    assert (
                        len(file_data) == entry["size"]
                    ), f"{entry["size"]=} {entry['diskSize']=} {len(file_data)=}"
                else:
                    # Handle other compression types if needed
                    pass
                # Save the decompressed data to a file
                out_path = f"{entry['fileHash']:08x}.bin"
                with open(filename.split(".")[0] + "/" + out_path, "wb") as out_file:
                    out_file.write(file_data)
                print(f"Extracted {out_path} ({entry['size']} bytes)")
            f.close()
        else:
            print("Failed to read the BLB archive.")


if __name__ == "__main__":
    main()
