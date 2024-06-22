import json
import requests

games = []
params = {
    'page': 1,
    'tag': 'visual_novel',
    'order': '-priority',
    'referer': 'https://vkplay.ru/play/tags/visual_novel/',
}

r = requests.get('https://api.vkplay.ru/play/games/', params=params).json()
while r['next']:
    games += r['results']
    r = requests.get(r['next']).json()

games += r['results']
print(json.dumps(games))
