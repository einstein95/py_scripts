import json

import requests


def fetch_games():
    games = []
    params = {
        "page": 1,
        "tag": "visual_novel",
        "order": "-priority",
        "referer": "https://vkplay.ru/play/tags/visual_novel/",
    }

    with requests.Session() as session:
        response = session.get("https://api.vkplay.ru/play/games/", params=params)
        response.raise_for_status()
        data = response.json()

        while data.get("next"):
            games.extend(data["results"])
            response = session.get(data["next"])
            response.raise_for_status()
            data = response.json()

        games.extend(data["results"])

    return games


if __name__ == "__main__":
    games = fetch_games()
    print(json.dumps(games, indent=2))
