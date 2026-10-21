import requests

url = "https://api.opendota.com/api/heroes"
heroes = requests.get(url, timeout=10).json()

# Сортируем по ID героя
heroes_sorted = sorted(heroes, key=lambda h: h["id"])

print(f"{'ID':<4} | {'Имя героя':<24} | {'Атрибут':<8} | {'Тип атаки':<8} | Роли")
print("-" * 75)

for h in heroes_sorted:
    hero_id = h.get("id")
    name = h.get("localized_name")
    attr = h.get("primary_attr")  # str, agi, int, all
    attack = h.get("attack_type")  # Melee, Ranged
    roles = ", ".join(h.get("roles", []))[:25]

    print(f"{hero_id:<4} | {name:<24} | {attr:<8} | {attack:<8} | {roles}")
