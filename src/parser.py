from bs4 import BeautifulSoup
import requests

BASE_URL = "https://www.avaclinic.ru/prices/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def get_all_filter_targets(session: requests.Session) -> list[dict]:
    """Автоматически находит на странице все направления, категории и их ID."""
    print("Ищем все доступные направления и фильтры на странице цен...")
    resp = session.get(BASE_URL, headers=HEADERS)
    if resp.status_code != 200:
        print(f"Ошибка загрузки страницы: {resp.status_code}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    targets = []
    seen = set()

    # 1. Проверяем стандартные <select> (DIRECTION, SUBDIRECTION, CATEGORY)
    for select_name in ["DIRECTION", "SUBDIRECTION", "CATEGORY"]:
        select_tag = soup.find("select", {"name": select_name})
        if select_tag:
            for option in select_tag.find_all("option"):
                val = option.get("value", "").strip()
                name = option.get_text(strip=True)
                # Игнорируем пустые, нулевые и служебные пункты ("Выберите направление" и т.п.)
                if val and val.isdigit() and int(val) > 0:
                    key = (select_name, val)
                    if key not in seen and name:
                        seen.add(key)
                        targets.append({"name": name, "params": {select_name: val}})

    # 2. Если сайт использует кастомные выпадающие списки (div/li с data-атрибутами)
    if not targets:
        # Ищем элементы с атрибутами data-direction, data-value, data-category
        filter_elements = soup.find_all(
            lambda tag: any(
                attr in tag.attrs
                for attr in [
                    "data-direction",
                    "data-value",
                    "data-category",
                    "data-subdirection",
                ]
            )
        )

        for el in filter_elements:
            name = el.get_text(strip=True)
            # Определяем параметр и значение
            param_name = None
            val = None

            if el.get("data-direction"):
                param_name = "DIRECTION"
                val = el.get("data-direction")
            elif el.get("data-category"):
                param_name = "CATEGORY"
                val = el.get("data-category")
            elif el.get("data-subdirection"):
                param_name = "SUBDIRECTION"
                val = el.get("data-subdirection")
            elif el.get("data-value") and el.get("data-value").isdigit():
                # Проверяем имя родительского блока или data-type
                param_name = "DIRECTION"
                val = el.get("data-value")

            if param_name and val and val.isdigit() and int(val) > 0 and name:
                key = (param_name, val)
                if key not in seen:
                    seen.add(key)
                    targets.append({"name": name, "params": {param_name: val}})

    # 3. Дополнительно: поиск ссылок в меню прайс-листа (?DIRECTION=... или ?CATEGORY=...)
    if not targets:
        for a in soup.find_all(
            "a",
            href=lambda h: h and ("DIRECTION=" in str(h) or "CATEGORY=" in str(h)),
        ):
            href = a.get("href", "")
            name = a.get_text(strip=True)
            if not name:
                continue

            # Разбираем параметры ссылки
            query_part = href.split("?")[1] if "?" in href else href
            parts = [p.split("=") for p in query_part.split("&") if "=" in p]
            params = {
                k: v for k, v in parts if k in ["DIRECTION", "CATEGORY", "SUBDIRECTION"]
            }

            if params:
                key = tuple(sorted(params.items()))
                if key not in seen:
                    seen.add(key)
                    targets.append({"name": name, "params": params})

    print(f"Найдено фильтров / направлений: {len(targets)}")
    return targets
