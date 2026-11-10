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

if "search_history" not in st.session_state:
    st.session_state["search_history"] = []
if "found_entries" not in st.session_state:
    st.session_state["found_entries"] = None


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


# --- НАДШВИДКИЙ ПОШУК ПО БІНАРНИХ ФАЙЛАХ ---
def execute_fast_feather_search(pib_query, dr_query, ipn_query):
    # Шукаємо бінарні файли
    all_files = glob.glob("chunks/chunk_*.feather")
    if not all_files:
        st.error(
            "Помилка: бінарні файли не знайдені. Перевірте, чи завантажили ви файли .feather"
        )
        return []

    matched_records = []

    pib_norm = normalize_string(pib_query) if pib_query.strip() else ""
    dr_norm = normalize_string(dr_query) if dr_query.strip() else ""
    ipn_norm = normalize_string(ipn_query) if ipn_query.strip() else ""

    for f in all_files:
        # Читання бінарного feather відбувається майже миттєво
        chunk = pd.read_feather(f)

        # Швидка векторна фільтрація
        mask = pd.Series(True, index=chunk.index)

        if pib_norm:
            mask &= (
                chunk["Прізвище, імя, по батькові в/с"]
                .astype(str)
                .str.lower()
                .str.contains(pib_norm, regex=False)
            )
        if dr_norm:
            mask &= (
                chunk["Дата народження"]
                .astype(str)
                .str.lower()
                .str.contains(dr_norm, regex=False)
            )
        if ipn_norm:
            mask &= (
                chunk["РНОКПП"]
                .astype(str)
                .str.lower()
                .str.contains(ipn_norm, regex=False)
            )

        filtered_chunk = chunk[mask]
        if not filtered_chunk.empty:
            matched_records.extend(filtered_chunk.to_dict(orient="records"))

    return matched_records


# --- ІНТЕРФЕЙС ---
st.title("🔎 Система пошуку по захищеній базі")
st.info("⚡ База даних переведена на ультра-швидкий бінарний індекс.")

main_col, history_col = st.columns()

with main_col:
    st.markdown("### Введіть дані для пошуку:")
    search_pib = st.text_input("Введіть ПІБ (можна частково):")
    search_dr = st.text_input("Дата народження (напр. 25.12.1985):")
    search_ipn = st.text_input("РНОКПП (ІПН повністю або частина):")

    if st.button("🚀 Запустити пошук", type="primary"):
        if not (search_pib.strip() or search_dr.strip() or search_ipn.strip()):
            st.warning("Будь ласка, заповніть хоча б одне поле для пошуку.")
        else:
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

            with st.spinner("Миттєве сканування індексу..."):
                st.session_state["found_entries"] = execute_fast_feather_search(
                    search_pib, search_dr, search_ipn
                )

    if st.session_state["found_entries"] is not None:
        entries = st.session_state["found_entries"]
        st.subheader(f"📊 Знайдено збігів: {len(entries)}")

        if len(entries) > 0:
            display_limit = min(len(entries), 250)

            for idx in range(display_limit):
                item = entries[idx]

                pib_val = item.get("Прізвище, імя, по батькові в/с", "—")
                dr_val = item.get("Дата народження", "—")
                ipn_val = item.get("РНОКПП", "—")

                c_text, c_pop = st.columns([4, 1])

                with c_text:
                    st.markdown(
                        f"👤 **{pib_val}** | 📅 ДН: {dr_val} | 📂 РНОКПП: {ipn_val}"
                    )

                with c_pop:
                    with st.popover("📋 Деталі"):
                        st.markdown("### 📋 Повна інформація:")
                        for key, val in item.items():
                            st.markdown(f"**{key}:** {val}")

                st.markdown(
                    "<hr style='margin:4px 0px; border-top: 1px solid #ccc;'/>",
                    unsafe_allow_html=True,
                )

            if len(entries) > 250:
                st.info(
                    "Показано перші 250 результатів. Уточніть пошуковий запит."
                )
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
