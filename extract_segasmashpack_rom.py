import argparse
from pathlib import Path
from typing import Tuple

# Pre-define encode strings as constants
ENCODE_STRINGS = {
    "1": b"Encoded for KGen Ultra / Sega Smash Pack / Snake KML 1999! ",
    "2": b"Encoded for KGen Ultra / Sega Smash Pack II / Snake KML 1999! ",
    "p": b"Encoded for KGen Ultra / Sega Puzzle Pack / Snake KML 1999! ",
}


def main():
    parser = argparse.ArgumentParser(
        description="Encode or decode files for KGen Ultra / Sega Smash Pack"
    )

    # Action argument (encode or decode)
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "-e", "--encode", action="store_true", help="Encode the input file"
    )
    action_group.add_argument(
        "-d", "--decode", action="store_true", help="Decode the input file"
    )

    # Pack selection argument
    parser.add_argument(
        "-p",
        "--pack",
        choices=["1", "2", "p"],
        required=True,
        help="Pack type: 1 (Smash Pack), 2 (Smash Pack II), p (Puzzle Pack)",
    )

    # Input and output files
    parser.add_argument("input_file", help="Input file path")
    parser.add_argument(
        "output_file",
        nargs="?",
        default=None,
        help="Output file path (default: input filename with .kvq for encode or .bin for decode)",
    )

    args = parser.parse_args()

    # Determine output filename
    if args.output_file is None:
        input_path = Path(args.input_file)
        if args.encode:
            output_file = input_path.with_suffix(".kvq")
        else:  # decode
            output_file = input_path.with_suffix(".bin")
    else:
        output_file = args.output_file

    # Get encode string
    encode_string = ENCODE_STRINGS[args.pack]

    # Read input file
    with open(args.input_file, "rb") as f:
        in_bytes = f.read()

    # Process based on action
    if args.decode:
        out_bytes = decode(in_bytes, encode_string)
    else:  # args.encode
        out_bytes = encode(in_bytes, encode_string)

    # Write output file
    with open(output_file, "wb") as f:
        f.write(out_bytes)


def decode(in_bytes: bytes, encode_string: bytes) -> bytearray:
    """Decode bytes using XOR cipher with rolling scramble value."""
    if len(in_bytes) < 8:
        raise ValueError("Input file too short (must be at least 8 bytes)")

    scramble = 6
    encode_len = len(encode_string)
    out_file = bytearray(len(in_bytes) - 8)

    for i, encoded_byte in enumerate(in_bytes[8:]):
        encode_char = encode_string[i % encode_len]
        out_file[i] = ((encoded_byte ^ encode_char ^ 0x80) - scramble) & 0xFF
        scramble = (scramble + 3) & 0xFF  # Keep scramble in byte range

    return out_file


def encode(in_bytes: bytes, encode_string: bytes) -> bytearray:
    """Encode bytes using XOR cipher with checksum header."""
    scramble = 6
    encode_len = len(encode_string)
    data_len = len(in_bytes)

    # Pre-allocate output buffer
    out_file = bytearray(8 + data_len)
    check = 0

    for i, rom_byte in enumerate(in_bytes):
        encode_char = encode_string[i % encode_len]
        encoded_byte = ((rom_byte + scramble) & 0xFF) ^ 0x80 ^ encode_char
        out_file[8 + i] = encoded_byte
        scramble = (scramble + 3) & 0xFF
        check = (check + encoded_byte + rom_byte) & 0xFFFFFFFF

    # Write checksum header
    check_inv = (~check) & 0xFFFFFFFF
    out_file[0:4] = check.to_bytes(4, "little")
    out_file[4:8] = check_inv.to_bytes(4, "little")

    return out_file


if __name__ == "__main__":
    main()
