import re
from sys import argv

import requests


def netscape_format_cookie(cookie_dict):
    """Formats a dictionary of cookies into Netscape format.

    Args:
        cookie_dict: A dictionary of cookies (e.g., from dict_from_cookiejar).

    Returns:
        A string representing the cookies in Netscape format.
    """
    netscape_lines = []
    for name, value in cookie_dict.items():
        # Netscape format fields: domain, flag, path, secure, expiration, name, value
        netscape_line = f"terminal.lc\tTRUE\t/\tFALSE\t0\t{name}\t{value}"
        netscape_lines.append(netscape_line)
    return "\n".join(netscape_lines)


headers = {
    "Content-Type": "application/x-www-form-urlencoded",
}

fileID = argv[1]
s = requests.Session()
data = f"type=file&file={fileID}"

response = s.post("https://terminal.lc/data/", headers=headers, data=data).json()
session = response["session"]

data = f"type=download&file={fileID}&session={session}"

response = s.post("https://terminal.lc/data/", headers=headers, data=data)
print(response.json()["url"])

print(netscape_format_cookie(s.cookies))

# import requests

# cookies = {
#     'cf_clearance': '_oFCqsiAOUwACivygyMqQfVj5EzcmQseLZifDugj6jg-1748163884-1.2.1.1-p.sgDWqpc7b6FlvLoSAwZhOB7v8A44TzphGoIknYwPd_JpCLsmi1j5m3c3_nfMQykk.gFX5rfThq_ndkmIoQwxC3xUwf1hD8nK0jaUpVyKcP0SZDTtEPSMN03kV3nt13tuHs7fG9qQWimmoc_MBLn17UG0WsfXFEoeWtlX9lk_AosjC_jlbunc6F3esyNrrTieWMjxnVQyPj3otMXyTpjZXWfmdc0QEHrxhBIT1dzEz4m.2vVGu76im.dWbjBEfo.HT7qHyE0oxmkENyjhN8Myf981ROo2SPk.nskTPKqBMKX3UHnjtVP2szVlzDHypcaFiV3L1OFiWluSnlW4KUJxxJn1uKOo58j1HJUwSg0U0',
#     'session': 'd418692c4af1f07a09a3f8e835e0401c415f49df85b7099071e691a4672e751a241966ba80b76e5dc169b9c9da529ce0434e0007047d8cdb6dc3670f33423731',
# }

# headers = {
#     'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:138.0) Gecko/20100101 Firefox/138.0',
#     'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#     'Accept-Language': 'en-US,en;q=0.5',
#     # 'Accept-Encoding': 'gzip, deflate, br, zstd',
#     'Connection': 'keep-alive',
#     # 'Cookie': 'cf_clearance=_oFCqsiAOUwACivygyMqQfVj5EzcmQseLZifDugj6jg-1748163884-1.2.1.1-p.sgDWqpc7b6FlvLoSAwZhOB7v8A44TzphGoIknYwPd_JpCLsmi1j5m3c3_nfMQykk.gFX5rfThq_ndkmIoQwxC3xUwf1hD8nK0jaUpVyKcP0SZDTtEPSMN03kV3nt13tuHs7fG9qQWimmoc_MBLn17UG0WsfXFEoeWtlX9lk_AosjC_jlbunc6F3esyNrrTieWMjxnVQyPj3otMXyTpjZXWfmdc0QEHrxhBIT1dzEz4m.2vVGu76im.dWbjBEfo.HT7qHyE0oxmkENyjhN8Myf981ROo2SPk.nskTPKqBMKX3UHnjtVP2szVlzDHypcaFiV3L1OFiWluSnlW4KUJxxJn1uKOo58j1HJUwSg0U0; session=d418692c4af1f07a09a3f8e835e0401c415f49df85b7099071e691a4672e751a241966ba80b76e5dc169b9c9da529ce0434e0007047d8cdb6dc3670f33423731',
#     'Upgrade-Insecure-Requests': '1',
#     'Sec-Fetch-Dest': 'document',
#     'Sec-Fetch-Mode': 'navigate',
#     'Sec-Fetch-Site': 'same-site',
#     'Sec-Fetch-User': '?1',
#     'Priority': 'u=0, i',
#     'Pragma': 'no-cache',
#     'Cache-Control': 'no-cache',
# }

# response = requests.get(
#     'https://bash.terminal.lc/kTlSf72GMTkQeSA3DOHNDg1748253043d3f4ebc8921c0618a68637f7d4f594b0ed522467bd4f5cb1619c95a3fb4d0069/School_of_Lust_Win_0.9.3a.zip',
#     cookies=cookies,
#     headers=headers,
# )
