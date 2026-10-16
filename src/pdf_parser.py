from datetime import datetime
from pathlib import Path
import re
import pandas as pd
import pdfplumber
import requests

PDF_URL = "https://www.avaclinic.ru/upload/iblock/341/19xnp4z9h1vh0i5bavskwa30od3ip4t9/Preyskurant-uslug-AVA_PETER-25.09.2026.pdf"

# Настройка путей относительно проекта
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

PDF_FILE = DATA_DIR / "preyskurant.pdf"
EXCEL_FILE = DATA_DIR / f"ava_peter_parsed_{datetime.now().strftime('%Y-%m-%d')}.xlsx"


def download_pdf(url: str, output_path: Path):
    """Скачивает PDF-файл потоком, чтобы не перегружать память."""
    print(f"Скачиваем PDF по ссылке: {url}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, stream=True, timeout=30)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
    print(
        f"PDF успешно сохранен: {output_path} ({round(output_path.stat().st_size / 1024 / 1024, 2)} МБ)"
    )


def extract_data_from_pdf(pdf_path: Path) -> list[dict]:
    """Извлекает строки таблиц из всех страниц PDF."""
    records = []
    current_category = "Общий раздел"

    print("Начинаем обработку страниц PDF...")
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Всего страниц в файле: {total_pages}")

        for page_num, page in enumerate(pdf.pages, start=1):
            # Извлекаем таблицу со страницы
            table = page.extract_table()

            if not table:
                # Если сетка не явная, пробуем метод без строгих линий
                table = page.extract_table(
                    table_settings={
                        "vertical_strategy": "text",
                        "horizontal_strategy": "lines",
                    }
                )

            if not table:
                continue

            for row in table:
                # Очищаем ячейки от переносов строк и пробелов
                cleaned_row = [
                    re.sub(r"\s+", " ", cell).strip() if cell else "" for cell in row
                ]

                # Пропускаем пустые строки
                if not any(cleaned_row):
                    continue

                # Игнорируем повторяющиеся шапки таблиц
                row_str = " ".join(cleaned_row).lower()
                if (
                    "наименование" in row_str
                    and "цена" in row_str
                    or "код" in row_str
                    and "стоимость" in row_str
                ):
                    continue

                # Если в строке заполнена только одна ячейка — обычно это название раздела/подраздела
                non_empty = [c for c in cleaned_row if c]
                if len(non_empty) == 1 and len(cleaned_row) > 1:
                    current_category = non_empty[0]
                    continue

                # Предполагаем стандартную структуру из 3-4 колонок:
                # [Код услуги, Наименование, Цена] или [Номер, Код, Наименование, Цена]
                code = ""
                name = ""
                price_val = None

                # Ищем цену в последней или предпоследней колонке
                for cell in reversed(cleaned_row):
                    # Проверяем, есть ли в ячейке число цены
                    digits = re.sub(r"[^\d]", "", cell)
                    if digits and (
                        "руб" in cell.lower()
                        or len(digits) >= 2
                        and cell.replace(" ", "").isdigit()
                    ):
                        try:
                            price_val = int(digits)
                            break
                        except ValueError:
                            pass

                if price_val is not None:
                    # Извлекаем код и наименование
                    if len(cleaned_row) >= 3:
                        code = cleaned_row[0]
                        name = cleaned_row[1]
                    elif len(cleaned_row) == 2:
                        name = cleaned_row[0]

                    records.append(
                        {
                            "Раздел": current_category,
                            "Код услуги": code,
                            "Наименование услуги": name,
                            "Цена (руб.)": price_val,
                            "Страница": page_num,
                        }
                    )

            if page_num % 10 == 0 or page_num == total_pages:
                print(f"  Обработано страниц: {page_num}/{total_pages}...")

    return records


def main():
    # 1. Скачиваем свежий файл, если его еще нет
    if not PDF_FILE.exists():
        download_pdf(PDF_URL, PDF_FILE)
    else:
        print(f"Используем ранее скачанный файл: {PDF_FILE}")

    # 2. Парсим
    data = extract_data_from_pdf(PDF_FILE)

    # 3. Сохраняем в Excel
    if data:
        df = pd.DataFrame(data)
        # Удаляем дубликаты, если страница переносилась с повтором
        df = df.drop_duplicates(
            subset=["Код услуги", "Наименование услуги", "Цена (руб.)"]
        )

        df.to_excel(EXCEL_FILE, index=False, engine="openpyxl")
        print(f"\n🎉 Готово! Всего извлечено услуг: {len(df)}")
        print(f"Файл сохранен: {EXCEL_FILE}")
    else:
        print("Не удалось извлечь данные. Проверьте разметку первой страницы PDF.")


if __name__ == "__main__":
    main()
