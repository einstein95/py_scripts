#!/usr/bin/env python3
"""
PNG IDAT Chunk Length Repair Script
Fixes PNG files with invalid IDAT chunk lengths by recalculating correct lengths
"""

import os
import struct
import sys
import zlib


def read_chunk_smart(f):
    """Read a PNG chunk, detecting actual data length even when declared length is wrong"""
    offset = f.tell()
    # Read length (4 bytes)
    length_bytes = f.read(4)
    if len(length_bytes) < 4:
        return None

    declared_length = struct.unpack(">I", length_bytes)[0]

    # Read chunk type (4 bytes)
    chunk_type = f.read(4)
    if len(chunk_type) < 4:
        return None

    # Save position after chunk type
    data_start = f.tell()

    # If declared length is 0x2000 or suspiciously large, search for actual end
    if declared_length == 0x2000 or declared_length > 0x100000:
        search_len = 0x20000  # Read up to 128KB to find next chunk
        # Read the declared amount
        search_buffer = f.read(search_len)

        if len(search_buffer) < declared_length + 4:
            # Not enough data, use what we got
            chunk_data = (
                search_buffer[:-4] if len(search_buffer) >= 4 else search_buffer
            )
            crc_bytes = (
                search_buffer[-4:] if len(search_buffer) >= 4 else b"\x00\x00\x00\x00"
            )
        else:
            # Search for likely chunk boundaries (valid chunk type signatures)
            chunk_types = [
                b"IHDR",
                b"PLTE",
                b"IDAT",
                b"IEND",
                b"tRNS",
                b"gAMA",
                b"cHRM",
                b"sRGB",
                b"iCCP",
                b"tEXt",
                b"zTXt",
                b"iTXt",
                b"bKGD",
                b"pHYs",
                b"sBIT",
                b"sPLT",
                b"hIST",
                b"tIME",
            ]

            best_end = None

            # Search for next chunk signature (4 byte length + 4 byte type)
            for i in range(len(search_buffer) - 7):
                # Check if bytes at position i+4 to i+8 match a known chunk type
                potential_type = search_buffer[i + 4 : i + 8]
                if potential_type in chunk_types:
                    # Verify the 4 bytes before could be a reasonable length
                    potential_length_bytes = search_buffer[i : i + 4]
                    potential_length = struct.unpack(">I", potential_length_bytes)[0]
                    # Reasonable length check (not too large)
                    if potential_length < 0x10000000:  # Less than ~268MB
                        best_end = i
                        break

            if best_end is not None:
                # Found next chunk, so current chunk data ends at best_end - 4 (for CRC)
                chunk_data = search_buffer[: best_end - 4]
                crc_bytes = search_buffer[best_end - 4 : best_end]
                # Seek to the start of next chunk
                f.seek(data_start + best_end)
            else:
                # No next chunk found, use all read data
                chunk_data = search_buffer[:-4]
                crc_bytes = search_buffer[-4:]
    else:
        # Normal chunk reading
        chunk_data = f.read(declared_length)
        crc_bytes = f.read(4)

    return {
        "length": declared_length,
        "type": chunk_type,
        "data": bytes(chunk_data),
        "crc": crc_bytes,
        "actual_data_length": len(chunk_data),
    }


def calculate_crc(chunk_type, chunk_data):
    """Calculate CRC32 for chunk type + data"""
    return zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF


def write_chunk(f, chunk_type, chunk_data):
    """Write a PNG chunk with correct length and CRC"""
    length = len(chunk_data)
    crc = calculate_crc(chunk_type, chunk_data)

    f.write(struct.pack(">I", length))
    f.write(chunk_type)
    f.write(chunk_data)
    f.write(struct.pack(">I", crc))


def repair_png(input_path, output_path):
    """Repair PNG file with invalid IDAT chunk lengths"""

    # Check if input file exists
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found")
        return False

    with open(input_path, "rb") as f:
        # Read and verify PNG signature
        signature = f.read(8)
        png_signature = b"\x89PNG\r\n\x1a\n"

        if signature != png_signature:
            print("Error: Not a valid PNG file (invalid signature)")
            return False

        print(f"Processing: {input_path}")
        print("-" * 60)

        chunks = []
        idat_count = 0
        issues_found = 0

        # Read all chunks
        while True:
            chunk = read_chunk_smart(f)
            if chunk is None:
                break

            chunk_type_str = chunk["type"].decode("ascii", errors="ignore")

            # Check for length mismatch
            if chunk["length"] != chunk["actual_data_length"]:
                issues_found += 1
                print(f"⚠ Found {chunk_type_str} chunk with invalid length:")
                print(f"  Declared: {chunk['length']} bytes")
                print(f"  Actual:   {chunk['actual_data_length']} bytes")

            if chunk["crc"] != struct.pack(
                ">I", calculate_crc(chunk["type"], chunk["data"])
            ):
                print(
                    f"⚠ Found {chunk_type_str} chunk with invalid CRC. Recalculating."
                )
                issues_found += 1
                chunk["crc"] = struct.pack(
                    ">I", calculate_crc(chunk["type"], chunk["data"])
                )

            if chunk["type"] == b"IDAT":
                idat_count += 1

            chunks.append(chunk)

            # Stop after IEND chunk
            if chunk["type"] == b"IEND":
                break

        print("-" * 60)
        print(f"Summary:")
        print(f"  Total chunks: {len(chunks)}")
        print(f"  IDAT chunks: {idat_count}")
        print(f"  Chunks with invalid lengths: {issues_found}")
        print()

        if issues_found == 0:
            print("No issues found. File appears to be valid.")
            return True

        # Write repaired PNG
        print(f"Writing repaired PNG to: {output_path}")

        with open(output_path, "wb") as out_f:
            iend_seen = False
            # Write PNG signature
            out_f.write(png_signature)

            # Write all chunks with corrected lengths and CRCs
            for chunk in chunks:
                if chunk["type"] == b"IEND":
                    iend_seen = True
                write_chunk(out_f, chunk["type"], chunk["data"])

            if not iend_seen:
                print(
                    "⚠ Warning: No IEND chunk found in original file. Adding IEND chunk."
                )
                write_chunk(out_f, b"IEND", b"")

        print("✓ Repair complete!")
        return True


def main():
    if len(sys.argv) < 2:
        print("PNG IDAT Chunk Length Repair Tool")
        print("=" * 60)
        print("\nUsage:")
        print(f"  {sys.argv[0]} <input.png> [output.png]")
        print("\nExample:")
        print(f"  {sys.argv[0]} corrupted.png repaired.png")
        print(
            "\nIf output file is not specified, '_repaired' will be added to input filename"
        )
        sys.exit(1)

    input_path = sys.argv[1]

    # Generate output filename if not provided
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_repaired{ext}"

    success = repair_png(input_path, output_path)

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
