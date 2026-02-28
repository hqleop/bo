import sqlite3
import pandas as pd
import os
import sys
import re

# === ФАЙЛИ ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILE = os.path.join(BASE_DIR, "cpv_with_hierarchy.xlsx")
DB_FILE = os.path.join(BASE_DIR, "db.sqlite3")

if not os.path.isfile(DB_FILE):
    print(f"❌ Файл БД '{DB_FILE}' не знайдено.")
    sys.exit(1)

print(f"📁 Підключення до БД: {os.path.abspath(DB_FILE)}")

# === ЧИТАЄМО EXCEL (важливо: код як str) ===
df = pd.read_excel(EXCEL_FILE, dtype={"код": str})

# Нормалізація назв колонок
df.columns = df.columns.str.strip().str.lower()

required = {"код", "назва", "назва англійською"}
missing = required - set(df.columns)
if missing:
    print(f"❌ У Excel не вистачає колонок: {missing}")
    sys.exit(1)

def normalize_cpv_code(value: str):
    """
    Повертає cpv_code у вигляді:
    - '03111700-9' якщо є 9 цифр (відновлює дефіс)
    - '03111700' якщо лише 8 цифр
    - None якщо неможливо коректно витягнути 8+ цифр
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    s = str(value).strip()

    # прибираємо типові артефакти Excel: '03111700-9 ' , '31117009.0'
    s = s.replace("\u00a0", " ")  # NBSP
    s = s.strip()

    # Якщо вже у форматі 8digits-1digit
    m = re.match(r"^\s*(\d{8})-(\d)\s*$", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}"

    # Витягуємо тільки цифри
    digits = re.sub(r"\D", "", s)

    # Якщо Excel зʼїв дефіс і маємо 9 цифр -> відновлюємо
    if len(digits) == 9:
        return f"{digits[:8]}-{digits[8]}"

    # Якщо маємо 8 цифр — збережемо як є (без контрольної)
    if len(digits) == 8:
        return digits

    # Якщо float типу '3111700.0' -> digits може бути 7, тоді відкидаємо
    # Якщо більше 9 — беремо перші 9 (на випадок сміття в кінці)
    if len(digits) > 9:
        digits = digits[:9]
        if len(digits) == 9:
            return f"{digits[:8]}-{digits[8]}"
        if len(digits) == 8:
            return digits

    return None

# Формуємо потрібні колонки
out = pd.DataFrame({
    "cpv_code": df["код"].apply(normalize_cpv_code),
    "name_ua": df["назва"].astype(str).where(df["назва"].notna(), None),
    "name_en": df["назва англійською"].astype(str).where(df["назва англійською"].notna(), None),
})

# Відкидаємо рядки без коду
out = out[out["cpv_code"].notna()].copy()

# === ПІДКЛЮЧЕННЯ ДО БД ===
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# === СТВОРЕННЯ ТАБЛИЦІ (тільки потрібні поля) ===
cursor.execute("DROP TABLE IF EXISTS cpv_dictionary")
cursor.execute("""
CREATE TABLE cpv_dictionary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cpv_code TEXT NOT NULL,
    name_ua TEXT,
    name_en TEXT
)
""")

# Опційно: уникнути дублювань
cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_cpv_dictionary_code ON cpv_dictionary(cpv_code)")

# === ЗАЛИВКА ===
out.to_sql("cpv_dictionary", conn, if_exists="append", index=False)

conn.commit()
conn.close()

print("✅ cpv_dictionary створена і заповнена (cpv_code, name_ua, name_en).")