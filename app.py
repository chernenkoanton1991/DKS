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

# Ініціалізація історії пошуку та стану модального вікна
if "search_history" not in st.session_state:
    st.session_state["search_history"] = []
if "selected_row" not in st.session_state:
    st.session_state["selected_row"] = None


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


# --- НАДШВИДКИЙ КЕШ ДАНИХ (БАЗА ЗАВАНТАЖУЄТЬСЯ В ПАМ'ЯТЬ ОДИН РАЗ) ---
@st.cache_data
def load_entire_database():
    all_files = glob.glob("chunks/chunk_*.csv")
    if not all_files:
        return None

    df_list = []
    for f in all_files:
        chunk = pd.read_csv(f, dtype=str, sep=";")
        df_list.append(chunk)

    full_df = pd.concat(df_list, ignore_index=True)
    full_df = full_df.fillna("—")
    full_df = full_df.replace(r"^\s*$", "—", regex=True)

    # Створюємо приховані колонки для миттєвого пошуку без циклів
    full_df["_search_pib"] = (
        full_df["Прізвище, імя, по батькові в/с"]
        .astype(str)
        .apply(normalize_string)
    )
    full_df["_search_dr"] = (
        full_df["Дата народження"].astype(str).apply(normalize_string)
    )
    full_df["_search_ipn"] = full_df["РНОКПП"].astype(str).apply(normalize_string)

    return full_df


with st.spinner("⚡ Індексація бази даних для миттєвого пошуку..."):
    df = load_entire_database()

if df is None:
    st.error("Помилка: папка 'chunks' порожня або не знайдена.")
    st.stop()

# --- ІНТЕРФЕЙС ---
st.title("🔎 Система пошуку по захищеній базі")
st.success(f"⚡ База готова. Завантажено рядків: {len(df):,}")

main_col, history_col = st.columns([3, 1])

with main_col:
    st.markdown("### Введіть дані для пошуку:")
    search_pib = st.text_input(
        "Введіть ПІБ (можна частково, будь-який регістр):"
    )
    search_dr = st.text_input("Дата народження (напр. 25.12.1985):")
    search_ipn = st.text_input("РНОКПП (ІПН повністю або частина):")

    # Стан для збереження результатів поточного пошуку між перезапусками сторінки
    if "search_results" not in st.session_state:
        st.session_state["search_results"] = None

    if st.button("🚀 Запустити пошук", type="primary"):
        if not (search_pib.strip() or search_dr.strip() or search_ipn.strip()):
            st.warning("Будь ласка, заповніть хоча б одне поле для пошуку.")
        else:
            # Запис в історію
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

            # Миттєва фільтрація за допомогою заздалегідь підготовленого індексу
            mask = pd.Series(True, index=df.index)

            if search_pib.strip():
                mask &= df["_search_pib"].str.contains(
                    normalize_string(search_pib)
                )
            if search_dr.strip():
                mask &= df["_search_dr"].str.contains(
                    normalize_string(search_dr)
                )
            if search_ipn.strip():
                mask &= df["_search_ipn"].str.contains(
                    normalize_string(search_ipn)
                )

            # Зберігаємо знайдене (без прихованих колонок пошуку)
            display_cols = [
                c for c in df.columns if not c.startswith("_search_")
            ]
            st.session_state["search_results"] = df[mask][display_cols]

    # Відображення результатів та обробка кліків
    if st.session_state["search_results"] is not None:
        res = st.session_state["search_results"]
        st.subheader(f"📊 Знайдено збігів: {len(res)}")

        if len(res) > 0:
            # Використовуємо інтерактивний компонент з вибором рядків
            event = st.dataframe(
                res,
                use_container_width=True,
                on_select="rerun",
                selection_mode="single-row",
                key="dataframe_selection",
            )

            # Перевіряємо, чи вибрав користувач якийсь рядок
            if (
                event
                and "selection" in event
                and event["selection"]["rows"]
            ):
                selected_index = event["selection"]["rows"][0]
                st.session_state["selected_row"] = res.iloc[selected_index]
                st.rerun()
        else:
            st.warning("Нічого не знайдено за вашим запитом.")

with history_col:
    st.markdown("### 🕒 Історія пошуку:")
    if st.session_state["search_history"]:
        for item in reversed(st.session_state["search_history"]):
            st.write(f"• {item}")
        if st.button("Очистити історію"):
            st.session_state["search_history"] = []
            st.session_state["search_results"] = None
            st.rerun()
    else:
        st.write("*Історія порожня*")

# --- СПЛИВАЮЧЕ (МОДАЛЬНЕ) ВІКНО ДЛЯ ДЕТАЛЕЙ РЯДКА ---
if st.session_state["selected_row"] is not None:

    @st.dialog("📋 Детальна інформація про особу", width="large")
    def show_modal():
        row_data = st.session_state["selected_row"]

        # Виводимо всі стовпчики у вигляді списку або таблиці
        for column_name, value in row_data.items():
            st.markdown(f"**{column_name}:** `{value}`")

        st.write("---")
        if st.button("Закрити вікно", type="primary"):
            st.session_state["selected_row"] = None
            st.rerun()


    show_modal()
