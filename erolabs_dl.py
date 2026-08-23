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
if "data" in j:
    data = j["data"]

if isinstance(data, list):
    data = data[0]

if data["status"] == 1:
    # print(r.text)
    name = data["name"]
    ipa_url = data["iosIpaUrl"]
    if not (name and ipa_url):
        exit(1)
    print(f"{appid} = {name}")
    print(ipa_url)
else:
    exit(1)

r = requests.get(
    f"https://www.ero-labs.com/api/getSingleHGame", params={**params, "id": appid}
)
if not r.ok:
    exit()

j = r.json()
if "data" in j:
    data = j["data"]

if isinstance(data, list):
    data = data[0]

if data["status"] == 1:
    for i in [
        "android_demo_url",
        "android_url",
        "cloud_url",
        "ios_ipa_demo_url",
        "ios_testflight_url",
        "mac_demo_url",
        "mac_url",
        "nox_url",
        "webgl_url",
        "windows_demo_url",
        "windows_url",
    ]:
        if i in data and data[i] and "ldplayer" not in data[i]:
            print(data[i].replace("?openExternalBrowser=1", ""))
