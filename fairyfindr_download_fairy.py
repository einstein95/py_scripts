from random import shuffle
from sys import argv

import requests


def createHash():
    input = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    shuffledArray = list(input)
    shuffle(shuffledArray)
    return "".join(shuffledArray)[:100]


phone_number = argv[1]
gameHash = createHash()
data = {
    "fairy_phone": phone_number,
    "username": None,
    "email": None,
    "game_hash": gameHash,
}
requests.get(
    "https://beachsidebunnies.vip/wp-admin/admin-ajax.php?action=fairy_downloader",
    json=data,
)
