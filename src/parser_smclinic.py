import re
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
import requests

URL = "https://www.smclinic-spb.ru/uslugi/tseny-i-stoimost-uslug"

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


def clean_price(price_str: str) -> int | None:
    if not price_str:
        return None
    digits = re.sub(r"\D", "", price_str)
    return int(digits) if digits else None


def parse_smclinic() -> list[dict]:
    print(f"Загрузка страницы цен: {URL}...")
    session = requests.Session()
    response = session.get(URL, headers=HEADERS, timeout=30)

    if response.status_code != 200:
        print(f"Ошибка загрузки: статус {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    prices_container = soup.find("div", id="prices")

    if not prices_container:
        print("Контейнер #prices не найден.")
        return []

    results = []

    # Ищем все блоки слайдеров уровней (категорий)
    # level-1, level-2 содержат заголовки в slider_button и контент в slider_content
    sections = prices_container.find_all("div", class_=re.compile(r"slider.*level-"))

    for section in sections:
        # Заголовок текущего подраздела
        btn = section.find("div", class_="slider_button")
        section_name = btn.get_text(strip=True) if btn else "Общий раздел"

        # Контент внутри секции
        content_block = section.find("div", class_="slider_content")
        if not content_block:
            continue

        # Находим все таблицы с ценами
        tables = content_block.find_all("table", class_="just_show_price")

        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                name_td = row.find("td", class_="name")
                price_td = row.find("td", class_="price")

                if not name_td or not price_td:
                    continue

                service_name = name_td.get_text(strip=True)
                service_code = name_td.get("data-code", "").strip()
                price_raw = price_td.get_text(strip=True)
                price = clean_price(price_raw)

                if service_name:
                    results.append(
                        {
                            "Клиника": "СМ-Клиника (СПб)",
                            "Направление": section_name,
                            "Артикул": service_code,
                            "Услуга": service_name,
                            "Цена (руб.)": price,
                        }
                    )

    # Запасной сбор: если вложенные блоки не охватили всё, собираем напрямую все строки таблиц
    if not results:
        print("Пробуем прямой сбор по всем строкам таблиц...")
        all_rows = prices_container.find_all("tr")
        for row in all_rows:
            name_td = row.find("td", class_="name")
            price_td = row.find("td", class_="price")
            if name_td and price_td:
                service_name = name_td.get_text(strip=True)
                price = clean_price(price_td.get_text(strip=True))
                if service_name:
                    results.append(
                        {
                            "Клиника": "СМ-Клиника (СПб)",
                            "Направление": "Общее",
                            "Артикул": name_td.get("data-code", "").strip(),
                            "Услуга": service_name,
                            "Цена (руб.)": price,
                        }
                    )

    return results


def main():
    items = parse_smclinic()

    if not items:
        print("Не удалось извлечь услуги.")
        return

    df = pd.DataFrame(items)
    df = df.drop_duplicates(subset=["Артикул", "Услуга", "Цена (руб.)"])

    print(f"\nСбор завершен успешно!")
    print(f"Всего уникальных услуг: {len(df)}")
    print(f"Количество разделов: {df['Направление'].nunique()}")

    # Сохранение в папку data/
    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    output_file = data_dir / f"smclinic_spb_prices_{today}.xlsx"

    df.to_excel(output_file, index=False, engine="openpyxl")
    print(f"Файл сохранен: {output_file}")


if __name__ == "__main__":
    main()
