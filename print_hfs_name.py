#!/usr/bin/env python3
# coding: utf-8
from __future__ import annotations

import argparse
from pathlib import Path
from struct import unpack

DPME_SIGNATURE = b"PM"
SECTOR_SIZE = 512


def check_fs(iso: str) -> None:
    f = open(iso, "rb")

    f.seek(1 * SECTOR_SIZE)
    partition_num = 1
    partitions = []
    while True:
        if f.read(2) != DPME_SIGNATURE:
            break
        # Names, structure from https://github.com/apple-oss-distributions/IOStorageFamily/blob/main/IOApplePartitionScheme.h#L51
        f.seek(2, 1)  # dpme_reserved_1
        dpme_map_entries, dpme_pblock_start, dpme_pblocks = unpack(">III", f.read(12))
        dpme_name = f.read(32).decode("mac-roman").split("\x00")[0]
        dpme_type = f.read(32).decode("mac-roman").split("\x00")[0]
        dpme_lblock_start, dpme_lblocks, dpme_flags = unpack(">III", f.read(12))
        partitions.append(
            {
                "dpme_map_entries": dpme_map_entries,
                "dpme_pblock_start": dpme_pblock_start,
                "dpme_pblocks": dpme_pblocks,
                "dpme_name": dpme_name,
                "dpme_type": dpme_type,
                "dpme_lblock_start": dpme_lblock_start,
                "dpme_lblocks": dpme_lblocks,
                "dpme_flags": dpme_flags,
            }
        )
        # print(
        #     f"{dpme_map_entries=} {dpme_pblock_start=:#x} {dpme_pblocks=:#x} {dpme_name=} {dpme_type=} {dpme_lblock_start=:#x} {dpme_lblocks=:#x} {dpme_flags=:#x}"
        # )
        # Check if there are more partitions
        if partition_num <= dpme_map_entries:
            # Move onto the next partition
            partition_num += 1
            f.seek(partition_num * SECTOR_SIZE)
        else:
            # Finished parsing the partition map
            break
    for partition in partitions:
        if partition["dpme_type"] == "Apple_HFS":
            # print(f"Found HFS partition: {partition['dpme_name']}")
            f.seek(partition["dpme_pblock_start"] * SECTOR_SIZE)
            f.seek(0x400, 1)  # Skip the HFS boot block
            if f.read(2) == b"BD":
                # print("Found HFS partition")
                f.seek(0x22, 1)
                vn = unpack(">27p", f.read(27))[0].decode("mac-roman")
                print(f"{f.name}: {vn}")


def generate_parser() -> argparse.ArgumentParser:
    """
    Generate the parser

    The parser is split into multiple subparsers.
    One for each mode we support.

    Each subparser has a default function that handles that mode.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "src", metavar="INPUT", type=Path, nargs="+", help="Disk image(s)"
    )

    return parser


if __name__ == "__main__":
    parser = generate_parser()
    args = parser.parse_args()
    for fn in args.src:
        check_fs(fn)
