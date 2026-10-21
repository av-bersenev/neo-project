import time
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
import requests

BASE_URL = "https://www.avaclinic.ru/prices/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "*/*",
}


def get_all_directions(session: requests.Session) -> list[dict]:
    """Сбор всех чекбоксов DIRECTION с их ID и названиями."""
    print("Ищем все направления на странице цен...")
    resp = session.get(BASE_URL, headers=HEADERS)

    if resp.status_code != 200:
        print(f"Ошибка загрузки главной страницы: {resp.status_code}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    directions = []

    # Находим все чекбоксы с name="DIRECTION"
    inputs = soup.find_all("input", {"name": "DIRECTION"})

    for inp in inputs:
        d_id = inp.get("value")
        name = inp.get("data-name")

        if not name:
            label = soup.find("label", {"id": d_id})
            name = label.get_text(strip=True) if label else f"Направление_{d_id}"

        if d_id and d_id.isdigit():
            directions.append({"id": d_id, "name": name.strip()})

    print(f"Найдено направлений: {len(directions)}")
    return directions


def parse_direction(
    session: requests.Session, direction_id: str, direction_name: str
) -> list[dict]:
    """Парсит все страницы услуг конкретного направления."""
    page = 1
    direction_results = []
    seen_services = set()

    while True:
        if page == 1:
            params = {"DIRECTION": direction_id}
        else:
            params = {
                "DIRECTION": direction_id,
                "SERVICE_NAV": f"page-{page}",
                "ajax": "Y",
                "APPEND": "Y",
            }

        try:
            resp = session.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
        except Exception as e:
            print(f"  Ошибка запроса на стр. {page}: {e}")
            break

        if resp.status_code != 200:
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.find_all("div", class_="pricesSection_item")

        if not items:
            break

        # Проверка на повторы страниц
        first_title_el = (
            items[0].find("div", class_="pricesSection_name") if items else None
        )
        first_title = first_title_el.get_text(strip=True) if first_title_el else ""
        if first_title and first_title in seen_services:
            break
        seen_services.add(first_title)

        new_count = 0
        for item in items:
            name_tag = item.find("div", class_="pricesSection_name")
            name = name_tag.get_text(strip=True) if name_tag else "Без названия"

            # Основная цена
            price_tag = item.find("div", class_="pricesSection_value")
            price = None
            if price_tag:
                digits = "".join(
                    ch for ch in price_tag.get_text(strip=True) if ch.isdigit()
                )
                price = int(digits) if digits else None

            # Цена по подписке
            sub_tag = item.find("div", class_="pricesSection_wrap-subscride")
            sub_price = None
            if sub_tag:
                sub_digits = "".join(
                    ch for ch in sub_tag.get_text(strip=True) if ch.isdigit()
                )
                sub_price = int(sub_digits) if sub_digits else None

            direction_results.append(
                {
                    "Направление": direction_name,
                    "ID направления": direction_id,
                    "Услуга": name,
                    "Цена (руб.)": price,
                    "Цена по подписке (руб.)": sub_price,
                }
            )
            new_count += 1

        print(f"  [{direction_name}] Стр. {page}: добавлено {new_count} позиций")
        page += 1
        time.sleep(0.4)

    return direction_results


def main():
    session = requests.Session()

    # 1. Автоматически собираем все направления из инпутов
    directions = get_all_directions(session)

    if not directions:
        print("Направления не найдены. Проверьте соединение.")
        return

    all_data = []

    # 2. Проходимся циклом по каждому направлению
    for idx, d in enumerate(directions, 1):
        print(f"\n[{idx}/{len(directions)}] Сбор: {d['name']} (ID: {d['id']})")
        items = parse_direction(session, d["id"], d["name"])
        all_data.extend(items)
        print(f"Всего по направлению: {len(items)} услуг")

    # 3. Сохраняем в итоговый Excel
    if all_data:
        data_dir = Path(__file__).resolve().parent.parent / "data"
        data_dir.mkdir(exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = data_dir / f"avaclinic_all_prices_{today}.xlsx"

        df = pd.DataFrame(all_data)
        df = df.drop_duplicates(subset=["ID направления", "Услуга", "Цена (руб.)"])
        df.to_excel(file_path, index=False, engine="openpyxl")

        print(f"\n🎉 Сбор завершен! Всего выгружено уникальных услуг: {len(df)}")
        print(f"Файл сохранен: {file_path}")


if __name__ == "__main__":
    main()
