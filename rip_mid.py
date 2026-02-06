from struct import unpack
from sys import argv

search_sig = b"MThd"
input_file = open(argv[1], "rb").read()
num = 1
while True:
    try:
        offset = input_file.index(search_sig)
    except ValueError:
        break
    print(f"{offset=:#x}")
    filesize = 4
    m_seclen, m_ntracks = unpack(
        ">I2xH", input_file[offset + filesize : offset + filesize + 8]
    )
    print(f"MThd: {m_seclen=:#x} {m_ntracks=}")
    filesize += m_seclen + 4
    print(
        f"MThd: {offset=:#x} {filesize=:#x}",
        input_file[offset + filesize : offset + filesize + 4],
        input_file[offset : offset + filesize].hex(),
    )
    for i in range(m_ntracks):
        print(
            f"MTrk: {offset=:#x} {filesize=:#x}",
            input_file[offset + filesize : offset + filesize + 4],
        )
        if input_file[offset + 14 : offset + 18] != b"MTrk":
            raise ValueError("MTrk not found")
        filesize += 4
        m_seclen = unpack(">I", input_file[offset + filesize : offset + filesize + 4])[
            0
        ]
        if i == 0:
            # Parse the first track for any META_MARKER (6) events, which can have a filename
            track_offset = offset + filesize
            track_end = track_offset + 4 + m_seclen
            track_data = input_file[track_offset : track_offset + 4 + m_seclen]
            pos = track_offset + 4
            while pos < track_end:
                pos = track_data.find(
                    b"\xff\x06", pos - track_offset
                )  # META_MARKER event
                if pos == -1:
                    break
                length = track_data[pos + 2]
                pos += 3
                if length > 0:
                    filename_bytes = track_data[pos : pos + length]
                    try:
                        filename = filename_bytes.decode("utf-8")
                        print(f"Found filename in MIDI file: {filename}")
                    except UnicodeDecodeError:
                        print(
                            f"Found non-UTF-8 filename in MIDI file: {filename_bytes}"
                        )
                    break
                else:
                    pos += length
            break
        else:
            filesize += m_seclen + 4
    with open(f"{argv[1]}-{num:03}.mid", "wb") as of:
        of.write(input_file[offset : offset + filesize])
    input_file = input_file[offset + 1 :]
    num += 1
