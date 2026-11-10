import os
import re
import pandas as pd

# Назва вашого початкового великого файлу (повинен лежати в цій же папці)
input_file = "database.csv"
# Кількість рядків в одному файлі шматка (~30-40 МБ на файл)
chunk_size = 50000

# Створюємо папку chunks, якщо її немає
if not os.path.exists("chunks"):
    os.makedirs("chunks")


def clean_text(text):
    """Очищає текст для надійного порівняння: видаляє зайві пробіли на початку,

    всередині та в кінці, а також стандартизує всі види апострофів.
    """
    if pd.isna(text):
        return ""
    text = str(text).strip()
    # Замінюємо всі варіації апострофів на один класичний стандартний '
    text = re.sub(r"[’`‘]", "'", text)
    # Замінюємо подвійні/множинні пробіли всередині на один звичайний
    text = re.sub(r"\s+", " ", text)
    return text


print("🚀 Почалося розбиття та оптимізація великого файлу...")

# Зчитуємо великий CSV-файл частинами з розподільником ';'
for i, chunk in enumerate(
    pd.read_csv(input_file, chunksize=chunk_size, dtype=str, sep=";")
):
    # Очищаємо основні текстові колонки пошуку перед їх збереженням у шматки
    target_columns = [
        "Прізвище, імя, по батькові в/с",
        "Дата народження",
        "РНОКПП",
    ]

    for col in target_columns:
        if col in chunk.columns:
            chunk[col] = chunk[col].apply(clean_text)

    chunk_filename = f"chunks/chunk_{i}.csv"

    # Зберігаємо готові дрібні файли також через роздільник ';'
    chunk.to_csv(chunk_filename, index=False, sep=";")
    print(f"✅ Збережено шматок: {chunk_filename}")

print(
    "\n🎉 Успішно! Великий файл розбито та оптимізовано під нові назви стовпчиків."
)
print("Папка 'chunks' готова для відправки на GitHub через GitHub Desktop.")
