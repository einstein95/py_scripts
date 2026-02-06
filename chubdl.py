#!/usr/bin/env python3
import re
from sys import argv

import requests

s = requests.Session()
s.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    }
)

character = re.search(r"chub\.ai/characters/([^/]+)/([^/?]+)", argv[1])

if not character:
    print("Invalid Chub.ai character URL")
    exit(1)

char_json = s.get(
    f"https://gateway.chub.ai/api/characters/{character.group(1)}/{character.group(2)}"
)
if not char_json.ok:
    print("Failed to fetch character data")
    print(char_json.text)
    exit(1)

node_id = char_json.json()["node"]["id"]
params = {
    "ref": "main",
    "response_type": "blob",
}

response = s.get(
    f"https://gateway.chub.ai/api/v4/projects/{node_id}/repository/files/card.json/raw",
    params=params,
)
with open(f"main_{character.group(2)}_spec_v2.json", "wb") as f:
    f.write(response.content)
