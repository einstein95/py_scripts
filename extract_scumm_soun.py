#!/usr/bin/env python3

import os
import sys
import wave
from io import BufferedReader
from struct import unpack


def extract_bundle(input_file: str) -> None:
    with open(input_file, "rb") as f:
        base, ext = os.path.splitext(input_file)
        if ext and "." in base:
            input_file = os.path.splitext(base)[0] + ext
        else:
            input_file = base

        file_type, file_size = unpack(">4sI", f.read(8))
        print(f"{file_type=} {file_size=}")
        if file_type == b"FILE":
            file_size = f.seek(0, 2)
            f.seek(0)
            while f.tell() < file_size:
                extract_file(f)
        elif file_type not in (b"SOUN", b"TLKB"):
            extract_sdat(input_file, f)
        elif input_file.startswith("SOUN_"):
            extract_sdat(input_file, f, extract_only_first_file=True)
        else:
            while f.tell() < file_size:
                print(f.tell(), file_size)
                extract_sdat(f"{input_file}-{f.tell():08x}", f)


def extract_sdat(
    filename: str, f: BufferedReader, extract_only_first_file=False
) -> None:
    file_subtype, _ = unpack(">4sI", f.read(8))
    if file_subtype == b"\x93\x90\x70\x5f":
        output_file = f"{filename}.voc"
        f.seek(8)
        data = f.read()
        with open(output_file, "wb") as wav_file:
            data = b"Creative Voice File\x1a\x1a\x00\x0a\x01\x29\x11" + data
            wav_file.write(data)
            # wav_file.setnchannels(1)
            # wav_file.setsampwidth(1)
            # wav_file.setframerate(11025)
            # wav_file.writeframes(data)
            return
    file_subtype = file_subtype.decode()
    chunksize_diff = 8 if file_subtype not in ("SOU ", "iMUS") else 0

    while True:
        chunk_type, chunk_size = unpack(">4sI", f.read(8))
        print(f"{chunk_type=} {chunk_size=}")
        if chunk_type in [b"SDAT", b"DATA", b"ADL ", b"ROL ", b"SPK ", b"SBL "]:
            break
        f.seek(chunk_size - chunksize_diff, 1)

    if extract_only_first_file:
        data = f.read()
    else:
        data = f.read(chunk_size - chunksize_diff)
    output_file = None

    file_subtype = file_subtype.strip()
    if file_subtype in ("DIGI", "TALK"):
        output_file = f"{filename}.{file_subtype}.wav"
        with wave.open(output_file, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(1)
            wav_file.setframerate(11025)
            wav_file.writeframes(data)
    elif file_subtype == "MRAW":
        output_file = f"{filename}.{file_subtype}.wav"
        with wave.open(output_file, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(11025)
            wav_file.writeframes(data)
    else:
        if data[:4] == b"FORM":
            ext = "XMI"
        elif data[:4] == b"MThd":
            ext = "MID"
        elif data[:4] == b"MDhd":
            skip_len = unpack(">I", data[4:8])[0]
            data = data[skip_len + 8 :]
            ext = "MID"
        elif data[:4] == b"AUhd":
            data = data[0x13:]
            data = b"Creative Voice File\x1a\x1a\x00\x0a\x01\x29\x11" + data
            ext = "VOC"
        else:
            ext = file_subtype
        if chunk_type in (b"ADL ", b"ROL ", b"SPK ", b"SBL "):
            output_file = f"{filename}.{chunk_type.decode().strip()}.{ext}"
        else:
            output_file = f"{filename}.{ext}"
        with open(output_file, "wb") as out_f:
            out_f.write(data)

    print(f"Extracted SDAT chunk to {output_file}")


def extract_file(f: BufferedReader) -> None:
    tag, size = unpack(">4sI", f.read(8))
    assert tag == b"FILE", f"Expected 'FILE' tag, got {tag}"
    filename = f.read(13).decode().rstrip("\x00")
    print(f"Extracting {filename} ({size} bytes)")
    with open(filename, "wb") as out_f:
        out_f.write(f.read(size - 21))


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input_file>")
        sys.exit(1)
    for input_file in sys.argv[1:]:
        print(input_file)
        extract_bundle(input_file)
        os.remove(input_file)


if __name__ == "__main__":
    main()
