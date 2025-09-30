#!/usr/bin/env python3
import argparse
import re

import requests
from md2bbcode.main import process_html
from unidecode import unidecode

# from html2phpbbcode.parser import HTML2PHPBBCode


def main():
    parser = argparse.ArgumentParser(
        description="Fetch game information and thumbnail from Steam"
    )
    parser.add_argument("appid", type=str, help="The Steam app ID")
    parser.add_argument(
        "--lang",
        type=str,
        default="english",
        help="Language for game description (default: english)",
    )
    args = parser.parse_args()
    if "steam" in args.appid:
        args.appid = re.search(r"/app/(\d+)", args.appid).group(1)

    # p = HTML2PHPBBCode()
    r = requests.get(
        f"https://store.steampowered.com/api/appdetails",
        params={"appids": args.appid, "l": args.lang},
    )
    desc = r.json()[args.appid]["data"]["about_the_game"]
    print(desc)
    if args.lang == "english":
        desc = unidecode(desc)
    # print(p.feed(desc))
    print(process_html(desc))
    print(f"\n[From [url=https://store.steampowered.com/app/{args.appid}/]Steam[/url]]")

    r = requests.get(
        f"https://cdn.cloudflare.steamstatic.com/steam/apps/{args.appid}/library_600x900_{args.lang}_2x.jpg"
    )
    if not r.ok:
        r = requests.get(
            f"https://cdn.cloudflare.steamstatic.com/steam/apps/{args.appid}/library_600x900_2x.jpg"
        )
        if not r.ok:
            return
    with open("thumbnail.png", "wb") as of:
        of.write(r.content)


if __name__ == "__main__":
    main()
