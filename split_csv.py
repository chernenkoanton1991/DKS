import os
import re
import pandas as pd

input_file = "database.csv"
chunk_size = 70000  # Оптимальний розмір для швидкого читання

if not os.path.exists("chunks"):
    os.makedirs("chunks")


def clean_text(text):
    if pd.isna(text):
        return ""
    text = str(text).strip()
    text = re.sub(r"[’`‘]", "'", text)
    text = re.sub(r"\s+", " ", text)
    return text


print("🚀 Почалося швидкісне перепакування файлу у формат Feather...")

# Зчитуємо початковий CSV за роздільником ';'
for i, chunk in enumerate(
    pd.read_csv(input_file, chunksize=chunk_size, dtype=str, sep=";")
):
    target_columns = [
        "Прізвище, імя, по батькові в/с",
        "Дата народження",
        "РНОКПП",
    ]

    for col in target_columns:
        if col in chunk.columns:
            chunk[col] = chunk[col].apply(clean_text)

    # Заповнюємо пусті клітинки дефісом заздалегідь, щоб не гаяти час на сайті
    chunk = chunk.fillna("—")
    chunk = chunk.replace(r"^\s*$", "—", regex=True)

    # Зберігаємо у надшвидкому бінарному форматі .feather
    chunk_filename = f"chunks/chunk_{i}.feather"
    # Скидаємо індекси, бо feather вимагає стандартні індекси
    chunk = chunk.reset_index(drop=True)
    chunk.to_feather(chunk_filename)
    print(f"✅ Оптимізовано та збережено: {chunk_filename}")

print(
    "\n🎉 Успішно! Старі файли .csv з папки chunks можна видалити, залишивши тільки нові файли .feather"
)
