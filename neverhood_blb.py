import os
import struct
import wave
from sys import argv

import dclimplode  # type: ignore

known_hashes = {
    0x0002486A: "asRecFont",
    0x00302110: "sqDefault",
    0x0050004E: "paPodBlack",
    0x00918480: "stLineagex",
    0x01020D70: "HitArray",
    0x02038082: "paPodShade",
    0x041020CB: "bgRecPanelStart2",
    0x041023CB: "bgRecPanelStart1",
    0x04208A1C: "bgFatherHeader",
    0x0434000D: "meNumRows",
    0x04720052: "paPodFloor",
    0x0800A048: "ClickSwitch",
    0x0C05A30C: "bgQuaterHeader",
    0x1017021C: "paKlayFloor",
    0x240C2022: "meFirstChar",
    0x40041057: "fxDoorOpen24",
    0x40042057: "fxDoorOpen33",
    0x40401057: "fxDoorOpen20",
    0x404C0457: "fxDoorOpen03",
    0x40641057: "fxDoorOpen23",
    0x40642057: "fxDoorOpen32",
    0x4066014F: "fxDoorClose20",
    0x408C0034: "fx3LocksDisable",
    0x41050240: "meCharHeight",
    0x4225014F: "fxDoorClose32",
    0x4226014F: "fxDoorClose23",
    0x4425014F: "fxDoorClose33",
    0x4426014F: "fxDoorClose24",
    0x4600204C: "fxFogHornSoft",
    0x46431401: "GoToStartLoop/Finish",
    0x48442057: "fxDoorOpen38",
    0x530520E0: "meTracking",
    0x5410088A: "Ashooded",
    0x60352180: "meCharWidth",
    0x70230380: "paKlayShade",
    0x90100314: "paKlayBlack",
    0xB208B1B6: "meArchroArchRoomPath",
    0xC025014F: "fxDoorClose38",
    0xC2478500: "PopBalloon",
}

music = [
    0x00203197,
    0x04020210,
    0x05343184,
    0x061880C6,
    0x06333232,
    0x11482B95,
    0x31114225,
    0x601C908C,
    0x62222CAE,
    0x624A220E,
    0xB110382D,
    0xD2FA4D14,
]


def open_blb_archive(filename):
    entries = []
    # ext_data = None

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
    # for filename in ["A.BLB", "C.BLB", "HD.BLB", "I.BLB", "M.BLB", "S.BLB", "T.BLB"]:
    for filename in argv[1:]:
        base_folder = filename.split(".")[0]
        entries = open_blb_archive(filename)

        f = open(filename, "rb")
        if entries is not None:
            os.makedirs(filename.split(".")[0], exist_ok=True)
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
                out_path = known_hashes.get(
                    entry["fileHash"], f"{entry['fileHash']:08x}"
                )
                if entry["fileHash"] in music:
                    out_path += ".wav"
                    with wave.open(base_folder + "/" + out_path, "wb") as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(11025)
                        wav_file.writeframes(file_data)
                else:
                    out_path += ".bin"
                    with open(base_folder + "/" + out_path, "wb") as out_file:
                        out_file.write(file_data)
                print(f"Extracted {out_path} ({entry['size']} bytes)")
            f.close()
        else:
            print("Failed to read the BLB archive.")


if __name__ == "__main__":
    main()
