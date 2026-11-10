import base64
import glob
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Пошукова База Даних", layout="wide")


# --- НАЛАШТУВАННЯ ФОНОВОГО ЗОБРАЖЕННЯ ---
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        return None


bg_image_base64 = get_base64_image("background.png")

if bg_image_base64:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(255, 255, 255, 0.91), rgba(255, 255, 255, 0.91)), url("data:image/png;base64,{bg_image_base64}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# Ініціалізація історії пошуку
if "search_history" not in st.session_state:
    st.session_state["search_history"] = []


# --- ПЕРЕВІРКА ПАРОЛЯ ---
def check_password():
    if "password_correct" not in st.session_state:
        st.subheader("🔒 Вхід до системи")
        pas = st.text_input("Введіть пароль для доступу:", type="password")
        if st.button("Увійти"):
            if pas == st.secrets["credentials"]["password"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Невірний пароль")
        return False
    return True


if not check_password():
    st.stop()


# --- НОРМАЛІЗАЦІЯ ДЛЯ ПОШУКУ ---
def normalize_string(s):
    s = str(s).lower().strip()
    s = re.sub(r"[’`‘]", "'", s)
    s = re.sub(r"\s+", " ", s)
    return s


# --- УЛЬТРА-ЛЕГКА ІНДЕКСАЦІЯ БАЗИ ДАНИХ (ЗАЙМАЄ МІНІМУМ ПАМ'ЯТІ) ---
@st.cache_data
def load_optimized_database():
    all_files = glob.glob("chunks/chunk_*.csv")
    if not all_files:
        return None

    records = []
    for f in all_files:
        chunk = pd.read_csv(f, dtype=str, sep=";")
        chunk = chunk.fillna("—")
        chunk = chunk.replace(r"^\s*$", "—", regex=True)

        # Конвертуємо у легкий формат списку словників
        for row in chunk.to_dict(orient="records"):
            # Одразу додаємо оптимізовані поля пошуку в словник
            row["_pib_norm"] = normalize_string(
                row.get("Прізвище, імя, по батькові в/с", "")
            )
            row["_dr_norm"] = normalize_string(
                row.get("Дата народження", "")
            )
            row["_ipn_norm"] = normalize_string(row.get("РНОКПП", ""))
            records.append(row)

    return records


with st.spinner("⚡ Створення надшвидкого індексу бази даних..."):
    db_records = load_optimized_database()

if db_records is None:
    st.error("Помилка: папка 'chunks' порожня або не знайдена.")
    st.stop()

# --- ІНТЕРФЕЙС ---
st.title("🔎 Система пошуку по захищеній базі")
st.success(f"⚡ База готова до миттєвого пошуку. Завантажено рядків: {len(db_records):,}")

main_col, history_col = st.columns([3, 1])

with main_col:
    st.markdown("### Введіть дані для пошуку:")
    search_pib = st.text_input("Введіть ПІБ:")
    search_dr = st.text_input("Дата народження (напр. 25.12.1985):")
    search_ipn = st.text_input("РНОКПП (ІПН повністю або частина):")

    # Стан для результатів пошуку
    if "found_entries" not in st.session_state:
        st.session_state["found_entries"] = None

    if st.button("🚀 Запустити пошук", type="primary"):
        if not (search_pib.strip() or search_dr.strip() or search_ipn.strip()):
            st.warning("Будь ласка, заповніть хоча б одне поле для пошуку.")
        else:
            # Збереження історії
            history_entry = []
            if search_pib.strip():
                history_entry.append(f"ПІБ: '{search_pib.strip()}'")
            if search_dr.strip():
                history_entry.append(f"ДН: '{search_dr.strip()}'")
            if search_ipn.strip():
                history_entry.append(f"РНОКПП: '{search_ipn.strip()}'")

            if history_entry:
                full_entry_text = ", ".join(history_entry)
                if (
                    not st.session_state["search_history"]
                    or st.session_state["search_history"][-1] != full_entry_text
                ):
                    st.session_state["search_history"].append(full_entry_text)

            pib_q = normalize_string(search_pib) if search_pib.strip() else ""
            dr_q = normalize_string(search_dr) if search_dr.strip() else ""
            ipn_q = normalize_string(search_ipn) if search_ipn.strip() else ""

            # Блискавичний пошук по пам'яті (соті частки секунди)
            matched = []
            for r in db_records:
                if pib_q and pib_q not in r["_pib_norm"]:
                    continue
                if dr_q and dr_q not in r["_dr_norm"]:
                    continue
                if ipn_q and ipn_q not in r["_ipn_norm"]:
                    continue
                matched.append(r)

            st.session_state["found_entries"] = matched

    # Відображення результатів через спливаючі поповери
    if st.session_state["found_entries"] is not None:
        entries = st.session_state["found_entries"]
        st.subheader(f"📊 Знайдено збігів: {len(entries)}")

        if len(entries) > 0:
            # Обмежуємо перші 300 записів для стабільності браузера
            display_count = min(len(entries), 300)

            # Робимо кастомну таблицю з інтерактивними спливаючими вікнами
            for idx in range(display_count):
                item = entries[idx]

                # Формуємо красивий рядок картки
                pib_val = item.get("Прізвище, імя, по батькові в/с", "—")
                dr_val = item.get("Дата народження", "—")
                vch_val = item.get("Військова частина", "—")

                # Головний рядок та кнопка спливаючого списку в одному рядку
                col_data, col_pop = st.columns([5, 1])

                with col_data:
                    st.markdown(
                        f"**{pib_val}** | ДН: {dr_val} | В/Ч: {vch_val}"
                    )

                with col_pop:
                    # Справжній спливаючий список/вікно, яке відкривається на місці без перезапусків
                    with st.popover("📋 Деталі"):
                        st.markdown("### Повна інформація:")
                        for key, val in item.items():
                            if not key.startswith("_"):
                                st.markdown(f"**{key}:** {val}")

                st.markdown("<hr style='margin:2px 0px;'/>", unsafe_allow_html=True)

            if len(entries) > 300:
                st.info("Показано перші 300 результатів. Уточніть пошуковий запит для звуження списку.")
        else:
            st.warning("Нічого не знайдено за вашим запитом.")

with history_col:
    st.markdown("### 🕒 Історія пошуку:")
    if st.session_state["search_history"]:
        for item in reversed(st.session_state["search_history"]):
            st.write(f"• {item}")
        if st.button("Очистити історію"):
            st.session_state["search_history"] = []
            st.session_state["found_entries"] = None
            st.rerun()
    else:
        st.write("*Історія порожня*")
