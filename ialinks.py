#!/usr/bin/env python3
from sys import argv

import requests

url = argv[1]
# r = requests.get('http://web.archive.org/__wb/sparkline',
#                  params={'output': 'json', 'url': url, 'collection': 'web'},
#                  headers={'Referer': 'http://web.archive.org'}).json()
# years = [i for i in r['years']]
# years.sort()

# for year in years:
#     j = requests.get('http://web.archive.org/__wb/calendarcaptures/2',
#                      params={'url': url, 'date': year, 'groupby': 'day'}).json()
#     for date, status, numcap in j['items']:
#         if numcap == 1:
#             print(status, f'http://web.archive.org/web/{year}{date:04}id_/{url}')
#         else:
#             r = requests.get('http://web.archive.org/__wb/calendarcaptures/2',
#                              params={'url': url, 'date': f'{year}{date:04}'}).json()
#             for time, _, _ in r['items']:
#                 print(status, f'http://web.archive.org/web/{year}{date:04}{time:06}id_/{url}')
response = requests.get(
    "https://web.archive.org/cdx/",
    params={
        "url": url,
        "matchType": "prefix",  # domain or prefix
        "fl": "statuscode,timestamp,original",
        "output": "json",
    },
)
try:
    entries = response.json()[1:]
except:
    print("Error: Invalid response from web archive.")
    print(response.text)
    exit(1)

# Filter out entries with status code 200 or "-"
entries = [
    (status_code, timestamp, original_url)
    for status_code, timestamp, original_url in entries
    if status_code in ["200", "-"]
]
entries.sort(key=lambda entry: entry[1])
for status_code, timestamp, original_url in entries:
    # print(status_code, f"https://web.archive.org/web/{timestamp}id_/{original_url}")
    print(f"https://web.archive.org/web/{timestamp}id_/{original_url}")
