#!/usr/bin/env python3
"""
Skunk key validation script
Usage: python script.py <name> <int1> <int2> ...
"""
# for i in *.cct; do projectorrays decompile --dump-chunks $i; done; py ~/py_scripts/rip_stxt.py **/STXT-* >/dev/null; grep -hwoP '#int:\[.+?\]' **/*.txt | sort -u
from sys import argv


def strip_spaces(s: str) -> str:
    """Remove spaces, newlines, and carriage returns."""
    return s.translate(str.maketrans("", "", " \n\r"))


def force_uppercase_alpha(s: str) -> str:
    """Convert to uppercase and keep only alphabetic characters."""
    return "".join(c.upper() for c in s if c.isalpha())


def make_key_name(name: str, code: str) -> str:
    """Generate key from name and code."""
    name = strip_spaces(name)
    if not name:
        return "NOMATCH"

    # Repeat name to fill 16 characters
    name_upper = force_uppercase_alpha(name)
    name_repeated = (name_upper * (16 // len(name_upper) + 1))[:16]

    return encrypt_string(name_repeated, code)


def encrypt_string(msg: str, key: str) -> str:
    """Encrypt message with key using XOR-based algorithm."""
    msg_len, key_len = len(msg), len(key)
    result: list[str] = []

    for i in range(16):
        xor_val = ord(msg[i % msg_len]) ^ ord(key[i % key_len])

        # If lowercase letter (97-122), convert to uppercase
        if 97 <= xor_val <= 122:
            result.append(chr(xor_val & 0xDF))
        else:
            # Generate fallback character
            idx = i + 1
            result.append(chr(min(65 + (idx % key_len) + (idx % msg_len), 90)))

    return "".join(result)


def check_key(name: str, key: str, ints: list[str]) -> None:
    """Check if name/key combination matches any of the provided integers."""
    for code in ints:
        if make_key_name(name, code) == key:
            print(name, key, code)


def main():
    if len(argv) < 2:
        print("Usage: python script.py <name> <int1> <int2> ...")
        return

    name = argv[1]  # User name, custom
    ints = argv[2:]  # ggrep -hw '#int' **/*.txt | sort -u

    # Generate key and check against all provided integers
    for code in ints:
        generated_key = make_key_name(name, code)
        check_key(name, generated_key, ints)


if __name__ == "__main__":
    main()
