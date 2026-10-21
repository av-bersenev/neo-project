import json
import requests

PRO_MATCHES_URL = "https://api.opendota.com/api/proMatches"

response = requests.get(PRO_MATCHES_URL)
matches = response.json()

print("Всего матчей в ответе:", len(matches))
print("Пример одного матча:")
print(json.dumps(matches[0], indent=2, ensure_ascii=False))

match_detail_url = "https://api.opendota.com/api/matches/9054536936"
detail_response = requests.get(match_detail_url)
detail_data = detail_response.json()

# Посмотрим, есть ли ключ picks_bans
picks_bans = detail_data.get("picks_bans", [])
print(f"Всего стадий драфта (пиков/банов): {len(picks_bans)}")
if picks_bans:
    print("Пример одной записи драфта:")
    print(picks_bans[0])
