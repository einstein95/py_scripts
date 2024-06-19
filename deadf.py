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


def escape_string(s: str) -> str:
    """
    Escapes special characters in a string for MacBinary compatibility.

    Args:
        s (str): The input string to escape.

    Returns:
        str: The escaped string.
    """
    special_chars = '/":*|\\?%<>\x7f'
    escaped_string = []

    for char in s:
        if char == "\x81":
            escaped_string.append("\x81\x79")
        elif char in special_chars or ord(char) < 0x20:
            escaped_string.append("\x81" + chr(0x80 + ord(char)))
        else:
            escaped_string.append(char)

    return "".join(escaped_string)


def file_to_macbin(
    datalen: int,
    rsrclen: int,
    create_date: int,
    mod_date: int,
    file_type: bytes,
    creator: bytes,
    flags: int,
    name: bytes,
) -> bytes:
    """
    Converts file metadata to MacBinary format.

    Args:
        datalen (int): The length of the data fork.
        rsrclen (int): The length of the resource fork.
        create_date (int): The file creation date in Mac timestamp format.
        mod_date (int): The file modification date in Mac timestamp format.
        file_type (bytes): A 4-byte string indicating the file type.
        creator (bytes): A 4-byte string indicating the creator.
        flags (int): File flags.
        name (bytes): The name of the file as a byte string.

    Returns:
        bytes: The file metadata in MacBinary format.

    The function packs the provided metadata into a MacBinary header,
    computes a CRC for error-checking, and returns the combined result.
    """
    old_flags = (flags >> 8) & 0xFF
    new_flags = flags & 0xFF

    macbin_header = struct.pack(
        ">x64p4s4sBxHHHBxIIIIHB14xIHBB",
        name,  # Filename (Pascal string)
        file_type,  # File type
        creator,  # Creator
        old_flags,  # Finder flags (old)
        0,  # Zeroed fields
        0,
        0,
        old_flags & 0x80,  # Finder flags (old, locked bit)
        datalen,  # Data fork length
        rsrclen,  # Resource fork length
        create_date,  # Creation date
        mod_date,  # Modification date
        0,  # GetInfo length
        new_flags,  # Finder flags (new)
        0,  # Zeroed fields
        0,
        129,  # Version number
        129,  # Minimum version needed to read the file
    )

    crc = crc_hqx(macbin_header, 0)
    macbin = macbin_header + struct.pack(">H2x", crc)

    return macbin


def punyencode(orig: str) -> str:
    """
    Encodes a string using Punycode, applying additional rules for special
    characters.

    Args:
        orig (str): The original input string to encode.

    Returns:
        str: The Punycode-encoded string with a prefix if necessary, or the
             original string.
    """
    s = escape_string(orig)
    encoded = s.encode("punycode").decode("ascii")

    # Punycode encoding adds a '-' at the end when there are no special
    # characters. Remove trailing '-' for comparison purposes.
    compare = encoded.rstrip("-")

    # Return the Punycode string prefixed with 'xn--' if the original and
    # comparison differ, or if the last character is a space or a dot.
    if orig != compare or compare[-1] in " .":
        return "xn--" + encoded
    return orig


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
    parser = argparse.ArgumentParser(
        description="Convert AppleDouble files to MacBinary"
    )
    parser.add_argument("input_file", type=str, help="Input file")
    parser.add_argument("data_fork", type=str, nargs="?", help="Data fork")
    parser.add_argument(
        "--japanese", action="store_true", help="Japanese filename parsing"
    )
    args = parser.parse_args()

    with open(args.input_file, "rb") as f:
        assert f.read(4) in [b"\x00\x05\x16\x07", b"\x00\x05\x16\x00"]
        assert f.read(4) == b"\x00\x02\x00\x00"
        f.seek(0x10, 1)
        num_ent = struct.unpack(">H", f.read(2))[0]

        entries = [struct.unpack(">III", f.read(0xC)) for _ in range(num_ent)]

    ent_data = {}
    for ent_id, ent_off, ent_len in entries:
        f.seek(ent_off)
        ent_data[ent_id] = f.read(ent_len)

    data_fork = ent_data.get(1, b"")
    if not data_fork and args.data_fork:
        try:
            with open(args.data_fork, "rb") as df:
                data_fork = df.read()
        except FileNotFoundError:
            pass

    rsrc_fork = ent_data.get(2, b"")
    file_name = ent_data.get(3, b"")

    if not file_name:
        file_name = os.path.basename(args.input_file).replace(".rsrc", "")
        file_name = re.sub(r"^\._", "", file_name)
        file_name = parse.unquote_to_bytes(file_name)
        try:
            encoding = "shift-jis" if args.japanese else "mac-roman"
            file_name = file_name.decode("utf-8").encode(encoding)
        except UnicodeDecodeError:
            pass

    try:
        crtime, modtime = struct.unpack(">ii8x", ent_data.get(8, b""))
        crtime += 3029529600  # AppleDouble is seconds from 2000-01-01
        modtime += 3029529600
    except TypeError:
        statinfo = os.stat(args.input_file)
        crtime = int(statinfo.st_ctime) + 2082844800
        modtime = int(statinfo.st_mtime) + 2082844800

    data = ent_data.get(9, b"XXXXXXXXXX")
    file_type, fcreator, fflags = struct.unpack(">4s4sH", data[:10])

    file_name_decoded = file_name.decode(
        "shift-jis" if args.japanese else "macroman"
    )
    print(
        file_name_decoded,
        len(data_fork),
        len(rsrc_fork),
        crtime,
        modtime,
        file_type,
        fcreator,
        fflags,
    )

    outfile_name = os.path.join(
        os.path.dirname(args.input_file), f"{file_name_decoded}.bin"
    )

    with open(outfile_name, "wb") as out_file:
        out_file.write(
            file_to_macbin(
                len(data_fork),
                len(rsrc_fork),
                crtime,
                (modtime if modtime > 0 else 0),
                file_type,
                fcreator,
                fflags,
                file_name,
            )
        )
        if data_fork:
            out_file.write(data_fork)
            out_file.write(b"\x00" * (-len(data_fork) % 128))
        if rsrc_fork:
            out_file.write(rsrc_fork)
            out_file.write(b"\x00" * (-len(rsrc_fork) % 128))

    os.utime(outfile_name, (modtime - 2082844800, modtime - 2082844800))


if __name__ == "__main__":
    main()
