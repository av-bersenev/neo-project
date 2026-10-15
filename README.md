# Near-Earth Objects (NEO) Data Pipeline

Пет-проект по Data Engineering: автоматизированный ETL-пайплайн для сбора, обработки и сохранения данных NASA о сближающихся с Землей астероидах (NeoWs API).

## Стек технологий
- **Язык:** Python 3 (requests, psycopg2/SQLAlchemy)
- **База данных:** PostgreSQL
- **Инфраструктура:** Docker, Docker Compose
- **Окружение:** Linux / Raspberry Pi

## Структура проекта
- `src/` — исходный код пайплайна (экстракция, трансформация, загрузка).
- `sql/` — DDL-схемы таблиц базы данных.
- `data/` — локальные выгрузки сырых данных (не отслеживаются в Git).
- `.venv/` — изолированное виртуальное окружение.

## Быстрый старт
1. Клонировать репозиторий:
   ```bash
   git clone git@github.com:av-bersenev/neo-project.git
   cd neo-project