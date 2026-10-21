from datetime import datetime
import json
from pathlib import Path
import re
from bs4 import BeautifulSoup
import pandas as pd
import requests

URL = "https://lahtaclinic.ru/price_list/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8",
}


def clean_price(val) -> int | None:
    if val is None:
        return None
    digits = re.sub(r"\D", "", str(val))
    return int(digits) if digits else None


def fetch_services() -> list[dict]:
    print(f"Загрузка страницы {URL}...")
    session = requests.Session()
    resp = session.get(URL, headers=HEADERS, timeout=25)

    if resp.status_code != 200:
        print(f"Ошибка загрузки страницы: код {resp.status_code}")
        return []

    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # 1. Извлекаем справочник направлений (категорий)
    department_map = {}

    # Ищем JSON со словарем категорий / отделений
    dep_matches = re.findall(
        r"(?:departments|categories|directions)\s*=\s*(\[\{.*?\}\]);", html
    )
    for m in dep_matches:
        try:
            deps_json = json.loads(m)
            for d in deps_json:
                d_id = d.get("id")
                d_name = d.get("title") or d.get("name")
                if d_id and d_name:
                    department_map[d_id] = d_name.strip()
        except Exception:
            pass

    # 2. Ищем тег <script>, где лежит массив с ценами (cost, title, id_rnova)
    services_raw = []
    scripts = soup.find_all("script")

    for script in scripts:
        text = script.string or ""
        if '"cost"' in text and '"title"' in text:
            # Находим массив объектов JSON
            match = re.search(r"(\[\s*\{.*?\"title\".*?\"cost\".*?\}\s*\])", text)
            if match:
                try:
                    services_raw = json.loads(match.group(1))
                    print(
                        f"Успешно извлечен JSON с услугами! Найдено: {len(services_raw)}"
                    )
                    break
                except Exception as e:
                    print(f"Ошибка парсинга JSON: {e}")

    # Если не сработал поиск по тегам, берем регуляркой по всему HTML
    if not services_raw:
        match = re.search(
            r"(\[\s*\{[^\n\r]*\"id_rnova\"[^\n\r]*\"cost\"[^\n\r]*\}\s*\])", html
        )
        if match:
            try:
                services_raw = json.loads(match.group(1))
                print(f"JSON найден через прямой поиск: {len(services_raw)} услуг")
            except Exception as e:
                print(f"Ошибка: {e}")

    if not services_raw:
        print("Не удалось извлечь массив услуг.")
        return []

    parsed_items = []
    for item in services_raw:
        title = item.get("title", "").strip()
        cost = clean_price(item.get("cost"))

        # Сопоставляем направление
        dep_ids = item.get("departmentId") or []
        direction_name = "Общее"
        if isinstance(dep_ids, list) and dep_ids:
            first_dep = dep_ids[0]
            direction_name = department_map.get(first_dep, f"Отделение_{first_dep}")
        elif isinstance(dep_ids, int | str):
            direction_name = department_map.get(dep_ids, f"Отделение_{dep_ids}")

        parsed_items.append(
            {
                "Клиника": "Lahta Clinic",
                "Направление": direction_name,
                "Услуга": title,
                "Цена (руб.)": cost,
                "Код услуги (МИС)": item.get("id_rnova", ""),
                "URL услуги": item.get("url", ""),
            }
        )

    return parsed_items


def main():
    items = fetch_services()

    if not items:
        print("Данные не собраны.")
        return

    df = pd.DataFrame(items)
    df = df.drop_duplicates(subset=["Услуга", "Цена (руб.)"])

    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    output_file = data_dir / f"lahtaclinic_prices_{today}.xlsx"

    df.to_excel(output_file, index=False, engine="openpyxl")
    print(f"\nФайл готов: {output_file}")
    print(f"Всего сохранено услуг: {len(df)}")


if __name__ == "__main__":
    main()
