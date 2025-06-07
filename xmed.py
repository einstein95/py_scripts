import os
from struct import unpack
from sys import argv


def process_binary_file(input_file):
    with open(input_file, "rb") as infile:
        unknown, data_size = unpack(">4xII", infile.read(12))
        print(input_file, unknown, data_size)

        remaining_size = infile.seek(0, 2) - 12
        infile.seek(12)
        assert data_size == remaining_size, "Data size mismatch"

        output_file = input_file.replace(".bin", "_out.bin")
        with open(output_file, "wb") as outfile:
            outfile.write(infile.read(data_size))

    os.remove(input_file)


if __name__ == "__main__":
    if len(argv) != 2:
        print("Usage: python xmed.py <input_file>")
    else:
        process_binary_file(argv[1])
