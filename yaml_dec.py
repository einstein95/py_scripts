"""
Decodes the base64-encoded strings from rvpacker's YAML output back into their original form
"""

from base64 import b64decode
import json
import re
import sys
import binascii


def dec(s: re.Match) -> str:
    if len(s.groups()) == 2:
        p = s.group(1)
        t = s.group(2)
        t = t.replace("\\n", "")
        use_quotes = t[0] == t[-1] == '"'
        if use_quotes:
            t = t[1:-1]
        try:
            d = b64decode(t)
        except binascii.Error:
            raise ValueError(f"Invalid base64 data: {t!r}")
        try:
            decoded = d.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"Invalid UTF-8 data: {d} ({t})")
        if use_quotes:
            decoded = json.dumps(decoded, ensure_ascii=False)
        return f"{p} {decoded}"
    else:
        t = s.group(1)
        t = t.replace("\\n", "")
        use_quotes = t[0] == t[-1] == '"'
        if use_quotes:
            t = t[1:-1]
        try:
            d = b64decode(t)
        except binascii.Error:
            raise ValueError(f"Invalid base64 data: {t!r}")
        try:
            decoded = d.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"Invalid UTF-8 data: {d} ({t})")
        if use_quotes:
            decoded = json.dumps(decoded, ensure_ascii=False)
        return decoded


with open(sys.argv[1], "r") as f:
    data = f.read()
    data = re.sub(r"^(\s+\S.+) !binary \|\-\s*([\S]+(?:\n\1  \S+)*)", dec, data)
    data = re.sub(r'!binary (["\w\+/=\\]+)', dec, data)

with open(sys.argv[1], "w") as f:
    f.write(data)
