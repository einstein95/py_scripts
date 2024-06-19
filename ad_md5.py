#!/usr/bin/python3
import macresources
from hashlib import md5
from os import path
from re import findall
from struct import unpack
from sys import argv

def escape_string(s: str) -> str:
    new_name = ""
    for char in s:
        if char == "\x81":
            new_name += "\x81\x79"
        elif char in '/":*|\\?%<>' or ord(char) < 0x20:
            new_name += "\x81" + chr(0x80 + ord(char))
        else:
            new_name += char
    return new_name


def needs_punyencoding(orig: str) -> bool:
    if not orig.isascii():
        return True
    if orig != escape_string(orig):
        return True
    if orig[-1] in " .":
        return True
    return False

def __main__():
    fn = argv[1].replace('.rsrc', '')
    is_data, is_rsrc = path.exists(fn), path.exists(fn+'.rsrc')
    if not is_rsrc:
        f = open(fn, 'rb')
        f.seek(0, -2)
        size = f.tell()
        f.seek(0)
    else:
        f = open(fn+'.rsrc', 'rb')
        pjver = 0
        m = macresources.parse_file(f.read())
        l = list(m)

        for r in l:
            if r.type in [b'XCOD', b'XCMD', b'XFCN']:
                print(f'Detected {r.type.decode("mac-roman")}: {r.name} ({r.id})')

        if len(argv) > 2:
            vers = [i for i in l if i.type == b'vers' and i.id == 1]
            if vers:
                vers = vers[0]
            else:
                print('!!! no vers.1 !!!')
                exit(1)

            major, minor = unpack('BB', bytes(vers)[:2])
            minor1 = minor >> 4
            minor2 = minor & (1 << 4) - 1
            # TODO: replace this with bitwise stuff?
            pjver = f'{major}{minor1}{minor2}'
            f.seek(0)
            rsrcoff, rsrclen = unpack('>I4xI', f.read(0xC))
            f.seek(rsrcoff)
            size = rsrclen

    m = md5(f.read(size if size < 5000 else 5000)).hexdigest()

    fn = path.split(argv[1])[-1]
    if needs_punyencoding(fn):
        fn = 'xn--' + escape_string(fn).encode('punycode').decode('ascii')

    if type(pjver) is int:
        pjver = pjvers[pjver]

    if len(argv) > 2:
        print(f'"{fn}", "{m}", {size}, {pjver}')
    else:
        print(f'"{fn}", "{m}", {size}')

__main__()