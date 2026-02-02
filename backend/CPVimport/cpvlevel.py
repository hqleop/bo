from pathlib import Path
import pandas as pd
import re

# === базова директорія (де лежить цей скрипт) ===
BASE_DIR = Path(__file__).resolve().parent

# === файли ===
EXCEL_INPUT = BASE_DIR / "cpv_v1.xlsx"
EXCEL_OUTPUT = BASE_DIR / "cpv_with_hierarchy.xlsx"

# === завантаження Excel ===
df = pd.read_excel(EXCEL_INPUT)
df.columns = df.columns.str.strip()  # прибираємо пробіли з назв колонок


def normalize_code(code):
    if pd.isna(code):
        return None

    digits = re.sub(r"\D", "", str(code))
    return digits[:8] if len(digits) >= 8 else None


def detect_levels(code):
    if not code or not isinstance(code, str):
        return 0, 0

    # Розділ XX000000
    if code[2:] == "000000":
        return code[:2], 0

    # Група XXX00000
    if code[3:] == "00000":
        return code[:3], code[:2]

    # Клас XXXX0000
    if code[4:] == "0000":
        return code[:4], code[:3]

    # Категорія XXXXXXXX
    return 0, code[:4]


# === нормалізація коду ===
df["cpv_clean"] = df["код"].apply(normalize_code)

# === розрахунок ієрархії ===
df[["рівень", "батьківський_рівень"]] = df["cpv_clean"].apply(
    lambda x: pd.Series(detect_levels(x))
)

# === збереження ===
df.drop(columns=["cpv_clean"], inplace=True)
df.to_excel(EXCEL_OUTPUT, index=False)

print("✅ CPV ієрархія успішно згенерована")
print(f"📄 Файл: {EXCEL_OUTPUT}")
