import re
import requests
import json
from sys import argv

if not argv[1].isdigit():
    print("invalid concept number")
    exit(1)

concept = argv[1]
for lang in ["en-gb", "en-hk", "ja-jp", "en-us"]:
    r = requests.get(f"https://store.playstation.com/{lang}/concept/{concept}")
    m = re.search(r'pdp-cta"><script[^>]+>(.+?)</script>', r.text)
    if not m:
        print("No script found")
        exit(1)
    j = json.loads(m.group(1))
    products = [i["__ref"] for i in j["cache"][f"Concept:{concept}"]["products"]]
    for p in products:
        print(
            j["cache"][p]["name"],
            f"https://store.playstation.com/{lang}/product/{p[8:]}",
        )
