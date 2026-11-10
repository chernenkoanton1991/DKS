import os
import re
import pandas as pd

input_file = "database.csv"
chunk_size = 50000  # Розмір одного шматка

if not os.path.exists("chunks"):
    os.makedirs("chunks")


def clean_text(text):
    """Очищає текст від зайвих пробілів та уніфікує апострофи."""
    if pd.isna(text):
        return ""
    text = str(text).strip()
    text = re.sub(r"[’`‘]", "'", text)  # Усі апострофи до одного виду
    text = re.sub(r"\s+", " ", text)  # Прибираємо подвійні пробіли
    return text


print("Почалося розбиття та оптимізація файлу...")

# Читаємо файл із роздільником ';'
for i, chunk in enumerate(
    pd.read_csv(input_file, chunksize=chunk_size, dtype=str, sep=";")
):
    # Нормалізуємо основні колонки пошуку перед збереженням
    for col in ["ПІБ", "Дата народження", "ІПН"]:
        if col in chunk.columns:
            chunk[col] = chunk[col].apply(clean_text)

    chunk_filename = f"chunks/chunk_{i}.csv"
    # Шматки зберігаємо теж через ';' для консистентності
    chunk.to_csv(chunk_filename, index=False, sep=";")
    print(f"Збережено частину: {chunk_filename}")

print(
    "\nУспішно! Великий файл розбито. Тепер database.csv можна видалити з папки, щоб не займати місце."
)
