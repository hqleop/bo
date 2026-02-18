import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db.sqlite3")

units = [
    # 📦 Штучні
    ("штука", "piece", "шт", "pcs", 1),
    ("комплект", "set", "компл", "set", 1),
    ("упаковка", "package", "упак", "pack", 1),
    ("коробка", "box", "кор", "box", 1),
    ("ящик", "crate", "ящ", "crate", 1),
    ("пара", "pair", "пар", "pair", 1),
    ("рулон", "roll", "рул", "roll", 1),
    ("лист", "sheet", "л", "sheet", 1),
    ("флакон", "bottle", "фл", "bottle", 1),
    ("банка", "jar", "бан", "jar", 1),

    # ⚖ Вага
    ("грам", "gram", "г", "g", 1),
    ("кілограм", "kilogram", "кг", "kg", 1),
    ("тонна", "tonne", "т", "t", 1),

    # 📏 Довжина
    ("міліметр", "millimeter", "мм", "mm", 1),
    ("сантиметр", "centimeter", "см", "cm", 1),
    ("метр", "meter", "м", "m", 1),
    ("кілометр", "kilometer", "км", "km", 1),

    # 📐 Площа
    ("квадратний метр", "square meter", "м²", "m2", 1),
    ("гектар", "hectare", "га", "ha", 1),

    # 🧪 Обʼєм
    ("мілілітр", "milliliter", "мл", "ml", 1),
    ("літр", "liter", "л", "l", 1),
    ("кубічний метр", "cubic meter", "м³", "m3", 1),

    # 🔥 Специфічні
    ("погонний метр", "linear meter", "пог.м", "lm", 1),
    ("людино-година", "man-hour", "люд.год", "mh", 1),
    ("машино-година", "machine-hour", "маш.год", "mach.h", 1),
    ("доба", "day", "доб", "day", 1),
    ("година", "hour", "год", "hour", 1),
]

def seed_units():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executemany("""
        INSERT OR IGNORE INTO core_unitofmeasure
        (name_ua, name_en, short_name_ua, short_name_en, is_active)
        VALUES (?, ?, ?, ?, ?)
    """, units)

    conn.commit()
    conn.close()
    print("✅ Units seeded successfully.")

if __name__ == "__main__":
    seed_units()
