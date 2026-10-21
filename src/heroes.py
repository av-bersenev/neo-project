import psycopg2
import requests

url = "https://api.opendota.com/api/heroes"

DB_CONFIG = {
    "dbname": "dota_analytics",
    "user": "dota_user",
    "password": "dota_password",
    "host": "localhost",
    "port": 5432,
}


def get_heroes():
    response = requests.get(url)
    data = response.json()
    return data


def save_heroes_to_db(heroes):
    # 1. Открываем соединение с базой
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    insert_query = """
        INSERT INTO dim_heroes (hero_id, name, localized_name, primary_attr, attack_type, roles)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (hero_id) DO NOTHING;
    """

    # 2. Проходим циклом for по каждому герою из списка
    for hero in heroes:
        values = (
            hero["id"],
            hero["name"],
            hero["localized_name"],
            hero["primary_attr"],
            hero["attack_type"],
            hero["roles"],
        )
        cursor.execute(insert_query, values)

    # 3. Фиксируем изменения
    conn.commit()

    # 4. Закрываем за собой курсор и соединение
    cursor.close()
    conn.close()
    print("Все герои успешно записаны в базу данных!")


# Точка входа — всегда в самом низу файла
if __name__ == "__main__":
    heroes = get_heroes()
    print("Всего героев получено:", len(heroes))
    save_heroes_to_db(heroes)
