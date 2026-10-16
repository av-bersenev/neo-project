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


def parse_target(
    session: requests.Session, target_name: str, base_params: dict
) -> list[dict]:
    """Универсальный сбор услуг для любого набора параметров (DIRECTION, CATEGORY и т.д.)."""
    page = 1
    target_results = []
    seen_services = set()

    while True:
        # Копируем базовые параметры фильтра
        params = base_params.copy()

        # Для страниц 2+ добавляем ajax-пагинацию Битрикса
        if page > 1:
            params["SERVICE_NAV"] = f"page-{page}"
            params["ajax"] = "Y"
            params["APPEND"] = "Y"

        try:
            resp = session.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
        except Exception as e:
            print(f"  Ошибка запроса на стр. {page}: {e}")
            break

        if resp.status_code != 200:
            print(f"  Страница {page} вернула статус {resp.status_code}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.find_all("div", class_="pricesSection_item")

        # Если услуг больше нет — пагинация закончилась
        if not items:
            break

        # Защита от зацикливания, если сервер при превышении страниц отдает первую
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

            target_results.append(
                {
                    "Раздел / Направление": target_name,
                    "Параметры фильтра": str(base_params),
                    "Услуга": name,
                    "Цена (руб.)": price,
                    "Цена по подписке (руб.)": sub_price,
                }
            )
            new_count += 1

        print(f"  [{target_name}] Стр. {page}: добавлено {new_count} позиций")
        page += 1
        time.sleep(0.4)

    return target_results


def main():
    session = requests.Session()

    # Список задач для сбора (можно передавать любые параметры из адресной строки сайта)
    targets = [
        {"name": "Акушерство и гинекология", "params": {"DIRECTION": "22"}},
        {"name": "Направление 19", "params": {"DIRECTION": "19"}},
        {"name": "Педиатрия", "params": {"DIRECTION": "38"}},
    ]

    all_data = []

    for t in targets:
        print(f"\nНачинаем сбор: {t['name']} с параметрами {t['params']}")
        items = parse_target(session, t["name"], t["params"])
        all_data.extend(items)
        print(f"Всего по {t['name']}: {len(items)} услуг")

    if all_data:
        data_dir = Path(__file__).resolve().parent.parent / "data"
        data_dir.mkdir(exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = data_dir / f"avaclinic_combined_{today}.xlsx"

        df = pd.DataFrame(all_data)
        # Удаляем дубликаты, если услуга дублируется в разных категориях
        df = df.drop_duplicates(
            subset=["Раздел / Направление", "Услуга", "Цена (руб.)"]
        )
        df.to_excel(file_path, index=False, engine="openpyxl")
        print(f"\nГотово! Выгружено {len(df)} уникальных строк в файл: {file_path}")


if __name__ == "__main__":
    main()
