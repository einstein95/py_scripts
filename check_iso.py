#!/usr/bin/python3
from sys import argv
from struct import unpack

APPLE_PM_SIGNATURE = b"PM\x00\x00"
SECTOR_SIZE = 512

disk_formats = []
if argv[1].startswith("http"):
    import requests
    from io import BytesIO

    r = requests.get(argv[1], headers={"Range": f"bytes=0-{0x8000+6}"})
    f = BytesIO(r.content)
else:
    f = open(argv[1], "rb")

# ISO Primary Volume Descriptor
f.seek(64 * SECTOR_SIZE)
if f.read(6) == b"\x01CD001":
    # print('Found ISO PVD')
    disk_formats.append("Win")

f.seek(0)
mac_1 = f.read(4)
f.seek(1 * SECTOR_SIZE)
mac_2 = f.read(4)
f.seek(2 * SECTOR_SIZE)
mac_3 = f.read(2)
if mac_2 == APPLE_PM_SIGNATURE:
    partition_num = 1
    partition_type = ""
    while True:
        num_partitions, partition_start, partition_size = unpack(">III", f.read(12))
        f.seek(32, 1)
        partition_type = f.read(32).decode("mac-roman").split("\x00")[0]
        if partition_type == "Apple_HFS":
            disk_formats.append("Mac")
            break
        # Check if there are more partitions
        if partition_num <= num_partitions:
            # Move onto the next partition
            partition_num += 1
            f.seek(partition_num * SECTOR_SIZE + 4)
# Bootable Mac-only disc
elif mac_1 == b"LK\x60\x00" and mac_3 == b"BD":
    disk_formats.append("Mac")

print(f'{"/".join(disk_formats)}\t{argv[1]}')
