#!/usr/bin/python3
from os.path import splitext
from struct import unpack
from sys import argv


def main():
    input_file = argv[1]

    with open(input_file, "rb") as file:
        # Read and decode disk name
        disk_name = unpack("64p", file.read(64))[0]
        print(disk_name.decode("mac-roman"))

        # Read disk length
        disk_length = unpack(">I", file.read(4))[0]

        # Extract disk data
        file.seek(0x54)
        output_file = splitext(input_file)[0] + ".dsk"
        with open(output_file, "wb") as output:
            output.write(file.read(disk_length))


if __name__ == "__main__":
    main()
