#!/usr/bin/env python3
# for i in *.cct; do projectorrays decompile --dump-chunks $i; done; py ~/py_scripts/rip_stxt.py **/STXT-* >/dev/null; grep -hwoP '#int:\[.+?\]' **/*.txt | sort -u
from sys import argv


def EncryptString(msg: str, key: str) -> str:
    msg_len, key_len = len(msg), len(key)
    result: list[str] = []

    for i in range(16):
        xor_val = ord(msg[i % msg_len]) ^ ord(key[i % key_len])
        if 97 <= xor_val <= 122:
            result.append(chr(xor_val & 0xDF))
        else:
            idx = i + 1
            result.append(chr(min(65 + (idx % key_len) + (idx % msg_len), 90)))
    return "".join(result)


def CheckKey(wName: str, wKey: str, wInts: list[str]) -> None:
    for n in wInts:
        # print("Checking", wName, wKey, n)
        if makeKeyName(wName, str(n)) == wKey:
            print(wName, wKey, n)


def makeKeyName(wName: str, wCode: str) -> str:
    wName = wName.replace(" ", "").upper()
    if not wName:
        return "NOMATCH"
    wName = (wName * (16 // len(wName) + 1))[:16]
    return EncryptString(wName, wCode)


name = argv[1]  # User name, custom
ints = argv[2:]  # ggrep -hw '#int' **/*.txt | sort -u
for i in ints:
    CheckKey(name, makeKeyName(name, i), ints)
