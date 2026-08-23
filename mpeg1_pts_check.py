#!/usr/bin/env python3
"""
mpeg1_pts_check.py
Parses an MPEG-1 Program Stream and reports audio PTS discontinuities.

Usage:
    python mpeg1_pts_check.py <file.mpg> [--threshold 0.1] [--verbose]

Arguments:
    file          Path to an MPEG-1 .mpg / .mpeg file
    --threshold   Allowed gap between consecutive audio PTSes in seconds (default 0.1)
    --verbose     Print every audio PTS found, not just discontinuities
"""

import argparse
import struct
import sys
from dataclasses import dataclass
from typing import Iterator, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PACK_START_CODE = b"\x00\x00\x01\xba"
SYSTEM_HEADER_CODE = b"\x00\x00\x01\xbb"
PACKET_START_CODE_PFX = b"\x00\x00\x01"

# Stream-id ranges (ISO 11172-1)
AUDIO_STREAM_ID_MIN = 0xC0
AUDIO_STREAM_ID_MAX = 0xDF
VIDEO_STREAM_ID_MIN = 0xE0
VIDEO_STREAM_ID_MAX = 0xEF

PTS_CLOCK_HZ = 90_000  # PTS ticks per second


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PESPacket:
    stream_id: int
    offset: int  # byte offset in the file
    pts: Optional[float]  # seconds, or None
    dts: Optional[float]


@dataclass
class Discontinuity:
    packet_index: int
    stream_id: int
    offset: int
    prev_pts: float
    curr_pts: float
    gap: float  # seconds (curr - prev); negative = backwards jump


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def read_pts(data: bytes, offset: int) -> int:
    """
    Decode a 33-bit PTS/DTS value from a 5-byte MPEG-1 PES timestamp field.
    Bit layout: [4 marker bits + 3 high] [15 mid] [15 low]
    """
    b = data[offset : offset + 5]
    if len(b) < 5:
        raise ValueError("Not enough bytes for PTS field")
    pts = (b[0] & 0x0E) << 29
    pts |= (b[1]) << 22
    pts |= (b[2] & 0xFE) << 14
    pts |= (b[3]) << 7
    pts |= (b[4] & 0xFE) >> 1
    return pts


def pts_to_seconds(pts: int) -> float:
    return pts / PTS_CLOCK_HZ


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def iter_pes_packets(path: str) -> Iterator[PESPacket]:
    """
    Walk through an MPEG-1 Program Stream and yield every PES packet header.
    Reads the file sequentially; does not load the whole file into RAM.
    """
    with open(path, "rb") as f:
        raw = f.read()  # MPEG-1 files are rarely > a few GB; mmap if needed

    pos = 0
    length = len(raw)

    while pos < length - 4:
        # Fast-scan for the 3-byte start-code prefix
        idx = raw.find(PACKET_START_CODE_PFX, pos)
        if idx == -1:
            break

        stream_id = raw[idx + 3]

        # Skip Pack header
        if stream_id == 0xBA:
            # MPEG-1 pack header: fixed 12 bytes
            pos = idx + 12
            continue

        # Skip System header
        if stream_id == 0xBB:
            if idx + 6 > length:
                break
            hdr_len = struct.unpack_from(">H", raw, idx + 4)[0]
            pos = idx + 6 + hdr_len
            continue

        # Only process audio/video PES packets (skip padding 0xBE, private, etc.)
        if not (
            AUDIO_STREAM_ID_MIN <= stream_id <= AUDIO_STREAM_ID_MAX
            or VIDEO_STREAM_ID_MIN <= stream_id <= VIDEO_STREAM_ID_MAX
        ):
            pos = idx + 4
            continue

        # PES packet length
        if idx + 6 > length:
            break
        pes_packet_length = struct.unpack_from(">H", raw, idx + 4)[0]
        header_start = idx + 6

        pts: Optional[float] = None
        dts: Optional[float] = None

        # Skip stuffing bytes (0xFF)
        p = header_start
        while p < length and raw[p] == 0xFF:
            p += 1

        if p >= length:
            pos = idx + 6 + pes_packet_length
            continue

        # STD buffer scale/size (optional, 2 bytes if top 2 bits are 01)
        if (raw[p] & 0xC0) == 0x40:
            p += 2

        if p >= length:
            pos = idx + 6 + pes_packet_length
            continue

        # PTS/DTS flags
        flags = raw[p] & 0xF0

        if flags == 0x20:  # PTS only
            try:
                pts_raw = read_pts(raw, p)
                pts = pts_to_seconds(pts_raw)
            except (ValueError, IndexError):
                pass
            p += 5

        elif flags == 0x30:  # PTS and DTS
            try:
                pts_raw = read_pts(raw, p)
                pts = pts_to_seconds(pts_raw)
            except (ValueError, IndexError):
                pass
            p += 5
            try:
                dts_raw = read_pts(raw, p)
                dts = pts_to_seconds(dts_raw)
            except (ValueError, IndexError):
                pass
            p += 5

        yield PESPacket(
            stream_id=stream_id,
            offset=idx,
            pts=pts,
            dts=dts,
        )

        pos = idx + 6 + pes_packet_length if pes_packet_length > 0 else idx + 4


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


def analyse(path: str, threshold: float, verbose: bool) -> None:
    last_pts: dict[int, float] = {}  # stream_id -> last seen pts (seconds)
    last_idx: dict[int, int] = {}  # stream_id -> packet index of last pts
    audio_count = 0
    disc_list: list[Discontinuity] = []

    for pkt_idx, pkt in enumerate(iter_pes_packets(path)):
        is_audio = AUDIO_STREAM_ID_MIN <= pkt.stream_id <= AUDIO_STREAM_ID_MAX

        if not is_audio:
            continue

        audio_count += 1

        if pkt.pts is None:
            if verbose:
                print(
                    f"  [#{pkt_idx:>6}] offset=0x{pkt.offset:08X}  "
                    f"stream=0x{pkt.stream_id:02X}  PTS=<none>"
                )
            continue

        if verbose:
            print(
                f"  [#{pkt_idx:>6}] offset=0x{pkt.offset:08X}  "
                f"stream=0x{pkt.stream_id:02X}  PTS={pkt.pts:.6f}s"
            )

        sid = pkt.stream_id
        if sid in last_pts:
            gap = pkt.pts - last_pts[sid]
            if abs(gap) > threshold:
                disc_list.append(
                    Discontinuity(
                        packet_index=pkt_idx,
                        stream_id=sid,
                        offset=pkt.offset,
                        prev_pts=last_pts[sid],
                        curr_pts=pkt.pts,
                        gap=gap,
                    )
                )

        last_pts[sid] = pkt.pts
        last_idx[sid] = pkt_idx

    # ---------------------------------------------------------------------------
    # Report
    # ---------------------------------------------------------------------------
    print(f"\n{'='*70}")
    print(f"File : {path}")
    print(f"Audio PES packets found : {audio_count}")
    print(f"Discontinuity threshold : {threshold:.3f}s")
    print(f"Discontinuities found   : {len(disc_list)}")
    print(f"{'='*70}")

    if not disc_list:
        print("\n✓  No audio PTS discontinuities detected.")
        return

    print()
    col = f"{'#':>6}  {'Offset':>10}  {'Stream':>6}  "
    col += f"{'Prev PTS (s)':>14}  {'Curr PTS (s)':>14}  {'Gap (s)':>12}  Note"
    print(col)
    print("-" * len(col))

    for d in disc_list:
        note = (
            "BACKWARDS JUMP" if d.gap < 0 else ("large gap" if d.gap > 1.0 else "gap")
        )
        print(
            f"{d.packet_index:>6}  "
            f"0x{d.offset:08X}  "
            f"0x{d.stream_id:02X}    "
            f"{d.prev_pts:>14.6f}  "
            f"{d.curr_pts:>14.6f}  "
            f"{d.gap:>+12.6f}  {note}"
        )

    print()
    if any(d.gap < 0 for d in disc_list):
        print("⚠  Backwards PTS jumps detected — likely a seek point or edit splice.")
    if any(d.gap > 1.0 for d in disc_list):
        print(
            "⚠  Gaps > 1 second detected — audio may cut out or stutter at those points."
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect audio PTS discontinuities in an MPEG-1 Program Stream."
    )
    parser.add_argument("file", help="Path to the MPEG-1 file (.mpg / .mpeg)")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.1,
        help="Maximum allowed PTS gap in seconds before flagging (default: 0.1)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every audio PTS, not just discontinuities",
    )
    args = parser.parse_args()

    try:
        analyse(args.file, args.threshold, args.verbose)
    except FileNotFoundError:
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
