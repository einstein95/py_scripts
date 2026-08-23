from sys import argv
from uuid import uuid4

import requests

appid = argv[1]
device_token = str(uuid4())

headers = {
    "User-Agent": "Mozilla/5.0 (iPad; CPU OS 11_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.0 Tablet/15E148 Safari/604.1",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "DeviceToken": device_token,
    "lang": "en",
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "keep-alive",
    "Referer": f"https://www.ero-labs.com/en/ios2/index.html?id={appid}",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

params = {
    "lang": "en",
    # "tv": "",
    # "betaId": "",
    # "preferenceTypes": "",
}

r = requests.get(
    f"https://www.ero-labs.com/api/v2/game/ios/{appid}",
    params=params,
    # cookies=cookies,
    headers=headers,
)

if not r.ok:
    exit(1)

j = r.json()
if "data" in j and j["data"]["status"] == 1:
    print(j["data"]["name"])
    print(j["data"]["iosIpaUrl"])
