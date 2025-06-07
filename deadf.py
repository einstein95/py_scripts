#!/usr/bin/env python3
"""
Convert AppleDouble files to MacBinary
"""
# Data Fork            1  Data fork
# Resource Fork        2  Resource fork
# Real Name            3  File’s name as created on home file system
# Comment              4  Standard Macintosh comment
# Icon, B&W            5  Standard Macintosh black and white icon
# Icon, Color          6  Macintosh color icon
# File Dates Info      8  File creation date, modification date, and so on
# Finder Info          9  Standard Macintosh Finder information
# Macintosh File Info 10  Macintosh file information, attributes, and so on
# ProDOS File Info    11  ProDOS file information, attributes, and so on
# MS-DOS File Info    12  MS-DOS file information, attributes, and so on
# Short Name          13  AFP short name
# AFP File Info       14  AFP file information, attributes, and so on
# Directory ID        15  AFP directory ID
import argparse
import os
import re
import struct
from binascii import crc_hqx
from urllib import parse


def escape_string(input_string: str) -> str:
    """
    Escapes special characters in a string for MacBinary compatibility.

    Args:
        input_string (str): The input string to escape.

    Returns:
        str: The escaped string.
    """
    special_characters = '/":*|\\?%<>\x7f'
    escaped_result = []

    for character in input_string:
        if character == "\x81":
            escaped_result.append("\x81\x79")
        elif character in special_characters or ord(character) < 0x20:
            escaped_result.append("\x81" + chr(0x80 + ord(character)))
        else:
            escaped_result.append(character)

    return "".join(escaped_result)


def convert_to_macbinary(
    data_fork_length: int,
    resource_fork_length: int,
    creation_date: int,
    modification_date: int,
    file_type_code: bytes,
    creator_code: bytes,
    file_flags: int,
    file_name: bytes,
) -> bytes:
    """
    Converts file metadata to MacBinary format.

    Args:
        data_fork_length (int): The length of the data fork.
        resource_fork_length (int): The length of the resource fork.
        creation_date (int): The file creation date in Mac timestamp format.
        modification_date (int): The file modification date in Mac timestamp format.
        file_type_code (bytes): A 4-byte string indicating the file type.
        creator_code (bytes): A 4-byte string indicating the creator.
        file_flags (int): File flags.
        file_name (bytes): The name of the file as a byte string.

    Returns:
        bytes: The file metadata in MacBinary format.

    The function packs the provided metadata into a MacBinary header,
    computes a CRC for error-checking, and returns the combined result.
    """
    old_file_flags = (file_flags >> 8) & 0xFF
    new_file_flags = file_flags & 0xFF

    macbinary_header = struct.pack(
        ">x64p4s4sBxHHHBxIIIIHB14xIHBB",
        file_name,  # Filename (Pascal string)
        file_type_code,  # File type
        creator_code,  # Creator
        old_file_flags,  # Finder flags (old)
        0,  # Zeroed fields
        0,
        0,
        old_file_flags & 0x80,  # Finder flags (old, locked bit)
        data_fork_length,  # Data fork length
        resource_fork_length,  # Resource fork length
        creation_date,  # Creation date
        modification_date,  # Modification date
        0,  # GetInfo length
        new_file_flags,  # Finder flags (new)
        0,  # Zeroed fields
        0,
        129,  # Version number
        129,  # Minimum version needed to read the file
    )

    crc_checksum = crc_hqx(macbinary_header, 0)
    macbinary_data = macbinary_header + struct.pack(">H2x", crc_checksum)

    return macbinary_data


def punycode_encode(original_string: str) -> str:
    """
    Encodes a string using Punycode, applying additional rules for special
    characters.

    Args:
        original_string (str): The original input string to encode.

    Returns:
        str: The Punycode-encoded string with a prefix if necessary, or the
             original string.
    """
    escaped_string = escape_string(original_string)
    punycode_encoded = escaped_string.encode("punycode").decode("ascii")

    # Punycode encoding adds a '-' at the end when there are no special
    # characters. Remove trailing '-' for comparison purposes.
    comparison_string = punycode_encoded.rstrip("-")

    # Return the Punycode string prefixed with 'xn--' if the original and
    # comparison differ, or if the last character is a space or a dot.
    if original_string != comparison_string or comparison_string[-1] in " .":
        return "xn--" + punycode_encoded
    return original_string


def main():
    """
    Main function for converting AppleDouble files to MacBinary format.

    This function processes an input AppleDouble file and optionally a data
    fork file, extracts necessary metadata, and converts the content to
    MacBinary format. The output file is saved in the same directory as the
    input file with a `.bin` extension.

    Command-line Arguments:
        input_file (str):            The path to the AppleDouble input file.
        data_fork (str, optional):   The path to the data fork file. If not
                                     provided, the data fork is extracted from
                                     the input file.
        --japanese (bool, optional): Flag indicating if Japanese filename
                                     parsing should be used.

    Raises:
        AssertionError: If the input file does not have the expected
                        AppleDouble header.
        FileNotFoundError: If the specified data fork file cannot be found.
    """
    argument_parser = argparse.ArgumentParser(
        description="Convert AppleDouble files to MacBinary"
    )
    argument_parser.add_argument("input_file", type=str, help="Input file")
    argument_parser.add_argument("data_fork", type=str, nargs="?", help="Data fork")
    argument_parser.add_argument(
        "--japanese", action="store_true", help="Japanese filename parsing"
    )
    arguments = argument_parser.parse_args()

    with open(arguments.input_file, "rb") as input_file:
        assert input_file.read(4) in [b"\x00\x05\x16\x07", b"\x00\x05\x16\x00"]
        assert input_file.read(4) == b"\x00\x02\x00\x00"
        input_file.seek(0x10, 1)
        num_entries = struct.unpack(">H", input_file.read(2))[0]

        entry_list = [
            struct.unpack(">III", input_file.read(0xC)) for _ in range(num_entries)
        ]

        entry_data = {}
        for entry_id, entry_offset, entry_length in entry_list:
            input_file.seek(entry_offset)
            entry_data[entry_id] = input_file.read(entry_length)

    data_fork_content = entry_data.get(1, b"")
    if not data_fork_content and arguments.data_fork:
        try:
            with open(arguments.data_fork, "rb") as data_fork_file:
                data_fork_content = data_fork_file.read()
        except FileNotFoundError:
            pass

    resource_fork_content = entry_data.get(2, b"")
    file_name_content = entry_data.get(3, b"")

    if not file_name_content:
        file_name_content = os.path.basename(arguments.input_file).replace(".rsrc", "")
        file_name_content = re.sub(r"^\._", "", file_name_content)
        file_name_content = parse.unquote_to_bytes(file_name_content)
        try:
            encoding_type = "shift-jis" if arguments.japanese else "mac-roman"
            file_name_content = file_name_content.decode("utf-8").encode(encoding_type)
        except UnicodeDecodeError:
            pass

    try:
        creation_time, modification_time = struct.unpack(
            ">ii8x", entry_data.get(8, b"")
        )
        creation_time += 3029529600  # AppleDouble is seconds from 2000-01-01
        modification_time += 3029529600
    except (TypeError, struct.error):
        file_stat_info = os.stat(arguments.input_file)
        creation_time = int(file_stat_info.st_ctime) + 2082844800
        modification_time = int(file_stat_info.st_mtime) + 2082844800

    finder_info = entry_data.get(9, b"XXXXXXXXXX")
    file_type_code, creator_code, finder_flags = struct.unpack(
        ">4s4sH", finder_info[:10]
    )

    decoded_file_name = file_name_content.decode(
        "shift-jis" if arguments.japanese else "macroman"
    )
    print(
        decoded_file_name,
        len(data_fork_content),
        len(resource_fork_content),
        creation_time,
        modification_time,
        file_type_code,
        creator_code,
        finder_flags,
    )

    output_file_name = os.path.join(
        os.path.dirname(arguments.input_file), f"{decoded_file_name}.bin"
    )

    with open(output_file_name, "wb") as output_file:
        output_file.write(
            convert_to_macbinary(
                len(data_fork_content),
                len(resource_fork_content),
                creation_time,
                (modification_time if modification_time > 0 else 0),
                file_type_code,
                creator_code,
                finder_flags,
                file_name_content,
            )
        )
        if data_fork_content:
            output_file.write(data_fork_content)
            output_file.write(b"\x00" * (-len(data_fork_content) % 128))
        if resource_fork_content:
            output_file.write(resource_fork_content)
            output_file.write(b"\x00" * (-len(resource_fork_content) % 128))

    os.utime(
        output_file_name,
        (modification_time - 2082844800, modification_time - 2082844800),
    )


if __name__ == "__main__":
    main()
