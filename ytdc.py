#!/usr/bin/env python3
import re
import sys
from datetime import datetime

import requests

r = requests.get(sys.argv[1])
m = re.search(r'(?<=<meta itemprop="startDate" content=")([^"]+)', r.text)
if not m:
    print("No date match found")
    sys.exit(1)
date = m.group(1)
# convert to unix timestamp
timestamp = datetime.fromisoformat(date)
m = re.search(r'(?<=<meta name="title" content=")([^"]+)', r.text)
if not m:
    print("No title match found")
    sys.exit(1)
title = m.group(1)
print(f"<t:{int(timestamp.timestamp())}:F> [{title}](<{sys.argv[1]}>)")
