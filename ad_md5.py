#!/usr/bin/python3
from hashlib import md5
from os import path
from struct import unpack
from sys import argv

import macresources  # type: ignore


def escape_string(input_string: str) -> str:
    escaped_name = ""
    for character in input_string:
        if character == "\x81":
            escaped_name += "\x81\x79"
        elif character in '/":*|\\?%<>' or ord(character) < 0x20:
            escaped_name += "\x81" + chr(0x80 + ord(character))
        else:
            escaped_name += character
    return escaped_name


def needs_punyencoding(original_string: str) -> bool:
    if not original_string.isascii():
        return True
    if original_string != escape_string(original_string):
        return True
    if original_string[-1] in " .":
        return True
    return False


def __main__():
    file_name = argv[1].replace(".rsrc", "")
    is_data_file, is_resource_file = path.exists(file_name), path.exists(
        file_name + ".rsrc"
    )
    proj_version = 0
    file_size = 0
    if not is_resource_file:
        file_handle = open(file_name, "rb")
        file_handle.seek(0, -2)
        file_size = file_handle.tell()
        file_handle.seek(0)
    else:
        file_handle = open(file_name + ".rsrc", "rb")
        resource_map = macresources.parse_file(file_handle.read())
        resource_list = list(resource_map)

        for resource in resource_list:
            if resource.type in [b"XCOD", b"XCMD", b"XFCN"]:
                print(
                    f'Detected {resource.type.decode("mac-roman")}: {resource.name} ({resource.id})'
                )

        if len(argv) > 2:
            version_resources = [
                res for res in resource_list if res.type == b"vers" and res.id == 1
            ]
            if version_resources:
                version_resource = version_resources[0]
            else:
                print("!!! no vers.1 !!!")
                exit(1)

            major_version, minor_version = unpack("BB", bytes(version_resource)[:2])
            minor_version_part1 = minor_version >> 4
            minor_version_part2 = minor_version & (1 << 4) - 1
            proj_version = f"{major_version}{minor_version_part1}{minor_version_part2}"
            file_handle.seek(0)
            resource_offset, resource_length = unpack(">I4xI", file_handle.read(0xC))
            file_handle.seek(resource_offset)
            file_size = resource_length

    file_hash = md5(
        file_handle.read(file_size if file_size < 5000 else 5000)
    ).hexdigest()

    file_name = path.split(argv[1])[-1]
    if needs_punyencoding(file_name):
        file_name = "xn--" + escape_string(file_name).encode("punycode").decode("ascii")

    # if type(proj_version) is int:
    #     proj_version = pjvers[proj_version]

    if len(argv) > 2:
        print(f'"{file_name}", "{file_hash}", {file_size}, {proj_version}')
    else:
        print(f'"{file_name}", "{file_hash}", {file_size}')


__main__()
