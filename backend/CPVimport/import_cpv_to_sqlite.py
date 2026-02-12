import sqlite3
import pandas as pd
import os
import sys

# === ФАЙЛИ ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILE = os.path.join(BASE_DIR, "cpv_with_hierarchy.xlsx")
DB_FILE = os.path.join(BASE_DIR, "db.sqlite3")

# === Перевірка, що файл БД існує ===
if not os.path.isfile(DB_FILE):
    print(f"❌ Файл БД '{DB_FILE}' не знайдено. Створіть його перед запуском скрипту.")
    sys.exit(1)

print(f"📁 Підключення до існуючої БД: {os.path.abspath(DB_FILE)}")

# === Читаємо Excel ===
df = pd.read_excel(EXCEL_FILE)

# === Відкидаємо рядки без cpv_code ===
if 'код' not in df.columns:
    print("❌ У Excel немає колонки 'код'")
    sys.exit(1)

df = df[df['код'].notna()]

# === Нормалізація назв колонок ===
df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)

# === Перейменування колонок для БД ===
df = df.rename(columns={
    "код": "cpv_code",
    "назва": "name_ua",
    "назва_англійською": "name_en",
    "рівень": "cpv_level_code",
    "батьківський_рівень": "cpv_parent_code",
})

# === Підключення до існуючої БД ===
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# === Дроп таблиці, якщо існує ===
cursor.execute("DROP TABLE IF EXISTS cpv_dictionary")

# === Створення таблиці з id, без parent_id ===
cursor.execute("""
CREATE TABLE cpv_dictionary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cpv_parent_code TEXT,
    cpv_level_code TEXT,
    cpv_code TEXT NOT NULL,
    name_ua TEXT,
    name_en TEXT
)
""")

# === Заливка даних ===
df.to_sql(
    "cpv_dictionary",
    conn,
    if_exists="append",
    index=False
)

conn.commit()
conn.close()

print("✅ Таблиця cpv_dictionary успішно створена в існуючій БД 'db'")
