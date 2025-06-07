#!/usr/bin/python3
from io import BytesIO
from struct import unpack
from sys import argv
from typing import Union

from _io import BufferedReader

APPLE_PARTITION_SIGNATURE = b"PM\x00\x00"
SECTOR_SIZE = 512

detected_formats = []

file_obj: Union[BytesIO, BufferedReader]
if argv[1].startswith("http"):
    import requests

    response = requests.get(argv[1], headers={"Range": f"bytes=0-32774"})  # 0x8006
    file_obj = BytesIO(response.content)
else:
    file_obj = open(argv[1], "rb")

# ISO Primary Volume Descriptor
file_obj.seek(64 * SECTOR_SIZE)
if file_obj.read(6) == b"\x01CD001":
    # print('Found ISO PVD')
    detected_formats.append("Win")

file_obj.seek(0)
mac_signature_1 = file_obj.read(4)
file_obj.seek(1 * SECTOR_SIZE)
mac_signature_2 = file_obj.read(4)
file_obj.seek(2 * SECTOR_SIZE)
mac_signature_3 = file_obj.read(2)
if mac_signature_2 == APPLE_PARTITION_SIGNATURE:
    partition_index = 1
    partition_type = ""
    while True:
        num_partitions, partition_start, partition_size = unpack(
            ">III", file_obj.read(12)
        )
        file_obj.seek(32, 1)
        partition_type = file_obj.read(32).decode("mac-roman").split("\x00")[0]
        if partition_type == "Apple_HFS":
            detected_formats.append("Mac")
            break
        # Check if there are more partitions
        if partition_index <= num_partitions:
            # Move onto the next partition
            partition_index += 1
            file_obj.seek(partition_index * SECTOR_SIZE + 4)
# Bootable Mac-only disc
elif mac_signature_1 == b"LK\x60\x00" and mac_signature_3 == b"BD":
    detected_formats.append("Mac")

print(f'{"/".join(detected_formats)}\t{argv[1]}')
