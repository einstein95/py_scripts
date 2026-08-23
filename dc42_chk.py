#!/usr/bin/python3
from struct import unpack
from sys import argv


def data_checksum(data: bytes) -> int:
    """
    Compute the checksum as described:
      - 32-bit accumulator starts at 0
      - for each big-endian 16-bit word in `data`:
          acc = (acc + word) & 0xFFFFFFFF   # add, ignoring overflow
          acc = rotate_right(acc, 1)        # rotate right by 1 bit
    `data` length must be a multiple of 2 bytes.
    """
    if len(data) % 2 != 0:
        raise ValueError("data length must be a multiple of 2 bytes")

    acc = 0x00000000
    mask = 0xFFFFFFFF

    for i in range(0, len(data), 2):
        word = (data[i] << 8) | data[i + 1]  # big-endian 16-bit word
        acc = (acc + word) & mask
        # rotate right by 1 bit within 32 bits
        acc = ((acc >> 1) | (acc << 31)) & mask

    return acc


def main():
    input_file = argv[1]

    with open(input_file, "rb") as file:
        # Read and decode disk name
        disk_name = unpack("64p", file.read(64))[0]
        print(disk_name.decode("mac-roman"))

        # Read disk length
        disk_length = unpack(">I", file.read(4))[0]

        file.seek(0x48)
        data_checksum_value = unpack(">I", file.read(4))[0]

        # Extract disk data
        file.seek(0x54)
        data = file.read(disk_length)
        checksum = data_checksum(data)
        print(f"{checksum:08x} ({checksum == data_checksum_value})")


if __name__ == "__main__":
    main()
