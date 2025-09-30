#!/usr/bin/env python3
import re
import sys
from datetime import datetime
from html import unescape

import requests


def fetch_data(url):
    r = requests.get(url)
    m = re.search(r'(?<=<meta itemprop="startDate" content=")([^"]+)', r.text)
    if not m:
        print("No date match found")
        return
    date = m.group(1)
    # convert to unix timestamp
    timestamp = datetime.fromisoformat(date)
    m = re.search(r'(?<=<meta name="title" content=")([^"]+)', r.text)
    if not m:
        print("No title match found")
        return
    title = unescape(m.group(1))
    m = re.search(r'(?<=<meta itemprop="identifier" content=")([^"]+)', r.text)
    if not m:
        print("No identifier match found")
        return
    url = "https://youtu.be/" + m.group(1)
    print(f"<t:{int(timestamp.timestamp())}:f> [{title}](<{url}>)")


for url in sys.argv[1:]:
    fetch_data(url)
