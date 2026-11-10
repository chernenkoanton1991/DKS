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


# --- ПЕРЕВІРКА ПАРОЛЯ ---
def check_password():
    if "password_correct" not in st.session_state:
        st.subheader("🔒 Вхід до системи")
        user = st.text_input("Логін")
        pas = st.text_input("Пароль", type="password")
        if st.button("Увійти"):
            if (
                user == st.secrets["credentials"]["username"]
                and pas == st.secrets["credentials"]["password"]
            ):
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Невірний логін або пароль")
        return False
    return True


if not check_password():
    st.stop()


# --- ЗАВАНТАЖЕННЯ ДАНИХ ---
@st.cache_data
def load_and_prepare_data():
    all_files = glob.glob("chunks/chunk_*.csv")
    if not all_files:
        return None

    # Читаємо шматки із роздільником ';'
    df_list = [pd.read_csv(f, dtype=str, sep=";") for f in all_files]
    combined_df = pd.concat(df_list, ignore_index=True)

    # Замінюємо порожні клітинки дефісом
    combined_df = combined_df.fillna("—")
    combined_df = combined_df.replace(r"^\s*$", "—", regex=True)

    return combined_df


with st.spinner("Завантаження інтерактивної бази даних..."):
    df = load_and_prepare_data()

if df is None:
    st.error("Помилка: папка 'chunks' порожня. Запустіть split_csv.py спочатку.")
    st.stop()


# --- НОРМАЛІЗАЦІЯ ДЛЯ ПОШУКУ ---
def normalize_string(s):
    s = str(s).lower().strip()
    s = re.sub(r"[’`‘]", "'", s)
    s = re.sub(r"\s+", " ", s)
    return s


# --- ІНТЕРФЕЙС ---
st.title("🔎 Система пошуку по захищеній базі")
st.write(f"У системі проіндексовано рядків: **{len(df):,}**")

st.markdown("### Введіть дані для пошуку:")
col1, col2, col3 = st.columns(3)

with col1:
    search_pib = st.text_input("Прізвище, імя, по батькові в/с")
with col2:
    search_dr = st.text_input("Дата народження (напр. 25.12.1985):")
with col3:
    search_ipn = st.text_input("РНОКПП (частина або повністю):")

if st.button("🚀 Запустити пошук", type="primary"):
    res = df.copy()

    # Фільтр ПІБ
    if search_pib.strip():
        norm_query = normalize_string(search_pib)
        res = res[
            res["ПІБ"].apply(
                lambda val: "" if val == "—" else normalize_string(val)
            ).str.contains(norm_query)
        ]

    # Фільтр Дата народження
    if search_dr.strip():
        norm_query = normalize_string(search_dr)
        res = res[
            res["Дата народження"]
            .apply(lambda val: "" if val == "—" else normalize_string(val))
            .str.contains(norm_query)
        ]

    # Фільтр ІПН
    if search_ipn.strip():
        norm_query = normalize_string(search_ipn)
        res = res[
            res["ІПН"]
            .apply(lambda val: "" if val == "—" else normalize_string(val))
            .str.contains(norm_query)
        ]

    # Результати
    st.subheader(f"📊 Знайдено збігів: {len(res)}")
    if len(res) > 0:
        st.dataframe(res, use_container_width=True)
    else:
        st.warning("Нічого не знайдено за вашим запитом.")
