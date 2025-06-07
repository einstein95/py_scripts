import sys
from struct import unpack

SOUND_NUM_TOC = 9
MUSIC_NUM_TOC = 4

input_name = sys.argv[1]
with open(input_name, "rb") as f:
    if input_name.lower() == "music.dat":
        num_toc = MUSIC_NUM_TOC
    elif input_name.lower() in ["sound.dat", "syncreds.dat"]:
        num_toc = SOUND_NUM_TOC
    else:
        print("Unknown file format.")
        sys.exit(1)
    f.seek(-4, 2)
    toc_offset = unpack("<I", f.read(4))[0]
    f.seek(toc_offset)
    # Skip the boolean fields of what tocs are used
    f.seek(2 * num_toc, 1)
    toc_offsets = []
    for _ in range(num_toc):
        offset, data_offset, toc_size = unpack("<iii4x", f.read(16))
        if offset == -1 or data_offset == -1 or toc_size == -1:
            continue
        toc_offsets.append((offset, data_offset, toc_size))
        print(f"{offset=:#x}, {data_offset=:#x}, {toc_size=:#x}")

    for offset, data_offset, toc_size in toc_offsets:
        if offset == -1 or data_offset == -1 or toc_size == -1:
            continue
        f.seek(offset)
        num_entries = toc_size // 0x20
        toc_entries = []
        for j in range(num_entries):
            file_name, file_offset, file_size = unpack("<18si4xi2x", f.read(32))
            if j == 0:
                # Skip the first entry, which is always empty (except file_size)
                continue
            if file_offset == -1 or file_size == -1:
                continue
            file_name = file_name.split(b"\0")[0].decode("utf-8")
            print(f"{file_name=}, {file_offset=:#x}, {file_size=:#x}")
            file_offset += data_offset
            toc_entries.append((file_name, file_offset, file_size))

        for file_name, file_offset, file_size in toc_entries:
            f.seek(file_offset)
            data = f.read(file_size)
            with open(file_name, "wb") as out_file:
                out_file.write(data)
