import base64
import glob
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Пошукова База Даних", layout="wide")


# --- НАЛАШТУВАННЯ ФОНОВОГО ЗОБРАЖЕННЯ ТА КОЛЬОРУ ТЕКСТУ ДЛЯ МОБІЛЬНИХ ---
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        return None


bg_image_base64 = get_base64_image("background.png")

# Примусово фіксуємо темний колір тексту для підписів полів (labels) на телефонах
st.markdown(
    """
    <style>
    /* Робимо підписи полів введення завжди чорними */
    label, .stWidgetLabel p, stMarkdownInsideButton p {
        color: #111111 !important;
        font-weight: 600 !important;
    }
    /* Заголовки */
    h1, h2, h3, h4, h5, h6, .stHeading p {
        color: #111111 !important;
    }
    /* Текст звичайних написів та інформаційного блоку */
    .stMarkdown p, .stText p, .stAlert p {
        color: #222222 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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

# Ініціалізація станів у сесії
if "search_history" not in st.session_state:
    st.session_state["search_history"] = []
if "found_entries" not in st.session_state:
    st.session_state["found_entries"] = None

# Тимчасові змінні для заповнення полів введення
if "input_pib" not in st.session_state:
    st.session_state["input_pib"] = ""
if "input_dr" not in st.session_state:
    st.session_state["input_dr"] = ""
if "input_ipn" not in st.session_state:
    st.session_state["input_ipn"] = ""


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
    all_files = glob.glob("chunks/chunk_*.feather")
    if not all_files:
        st.error("Помилка: бінарні файли не знайдені.")
        return []

    matched_records = []

    pib_norm = normalize_string(pib_query) if pib_query.strip() else ""
    dr_norm = normalize_string(dr_query) if dr_query.strip() else ""
    ipn_norm = normalize_string(ipn_query) if ipn_query.strip() else ""

    for f in all_files:
        chunk = pd.read_feather(f)
        mask = pd.Series(True, index=chunk.index)

        if pib_norm:
            mask &= (
                chunk["Прізвище, імя, по батькові в/с"]
                .astype(str)
                .str.lower()
                .str.contains(pib_norm, case=False, na=False, regex=False)
            )
        if dr_norm:
            mask &= (
                chunk["Дата народження"]
                .astype(str)
                .str.lower()
                .str.contains(dr_norm, case=False, na=False, regex=False)
            )
        if ipn_norm:
            mask &= (
                chunk["РНОКПП"]
                .astype(str)
                .str.lower()
                .str.contains(ipn_norm, case=False, na=False, regex=False)
            )

        filtered_chunk = chunk[mask]
        if not filtered_chunk.empty:
            matched_records.extend(filtered_chunk.to_dict(orient="records"))

    return matched_records


# --- ІНТЕРФЕЙС ---
st.title("🔎 Система пошуку по захищеній базі")
st.info("⚡ База даних переведена на ультра-швидкий бінарний індекс.")

# Використовуємо адаптивні колонки, які на мобільних пристроях автоматично переносяться одна під одну
main_col, history_col = st.columns([1, 1])

with main_col:
    st.markdown("### Введіть дані для пошуку:")

    search_pib = st.text_input(
        "Введіть ПІБ (можна частково):", value=st.session_state["input_pib"]
    )
    search_dr = st.text_input(
        "Дата народження (напр. 25.12.1985):", value=st.session_state["input_dr"]
    )
    search_ipn = st.text_input(
        "РНОКПП (ІПН повністю або частина):",
        value=st.session_state["input_ipn"],
    )

    if st.button("🚀 Запустити пошук", type="primary"):
        if not (search_pib.strip() or search_dr.strip() or search_ipn.strip()):
            st.warning("Будь ласка, заповніть хоча б одне поле для пошуку.")
        else:
            history_labels = []
            if search_pib.strip():
                history_labels.append(f"ПІБ: '{search_pib.strip()}'")
            if search_dr.strip():
                history_labels.append(f"ДН: '{search_dr.strip()}'")
            if search_ipn.strip():
                history_labels.append(f"РНОКПП: '{search_ipn.strip()}'")

            full_text = ", ".join(history_labels)

            new_history_item = {
                "text": full_text,
                "pib": search_pib.strip(),
                "dr": search_dr.strip(),
                "ipn": search_ipn.strip(),
            }

            if (
                not st.session_state["search_history"]
                or st.session_state["search_history"][-1]["text"] != full_text
            ):
                st.session_state["search_history"].append(new_history_item)

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

                # Оптимальне співвідношення для мобільних екранів
                c_text, c_pop = st.columns([0.75, 0.25])

                with c_text:
                    st.markdown(
                        f"👤 **{pib_val}** <br>📅 ДН: {dr_val} | 📂 РНОКПП: {ipn_val}",
                        unsafe_allow_html=True
                    )

                with c_pop:
                    with st.popover("📋 Деталі"):
                        st.markdown("### 📋 Повна інформація:")
                        for key, val in item.items():
                            st.markdown(f"**{key}:** {val}")

                st.markdown(
                    "<hr style='margin:6px 0px; border-top: 1px solid #ccc;'/>",
                    unsafe_allow_html=True,
                )

            if len(entries) > 250:
                st.info(
                    "Показано перші 250 результатів. Уточніть пошуковий запит."
                )
        else:
            st.warning("Нічого не знайдено за вашим запитом.")


# --- ІСТОРІЯ ПОШУКУ З ПОВТОРНИМ КЛІКОМ ---
with history_col:
    st.markdown("### 🕒 Історія пошуку:")
    if st.session_state["search_history"]:
        for h_idx, item in enumerate(
            reversed(st.session_state["search_history"])
        ):
            btn_key = f"replay_{len(st.session_state['search_history']) - 1 - h_idx}"

            st.write(f"• {item['text']}")

            if st.button("🔄 Повторити цей пошук", key=btn_key):
                st.session_state["input_pib"] = item["pib"]
                st.session_state["input_dr"] = item["dr"]
                st.session_state["input_ipn"] = item["ipn"]

                st.session_state["found_entries"] = execute_fast_feather_search(
                    item["pib"], item["dr"], item["ipn"]
                )
                st.rerun()

            st.markdown(
                "<div style='margin-bottom:15px; border-bottom: 1px dashed #ddd;'></div>",
                unsafe_allow_html=True,
            )

        if st.button("🗑️ Очистити всю історію"):
            st.session_state["search_history"] = []
            st.session_state["found_entries"] = None
            st.session_state["input_pib"] = ""
            st.session_state["input_dr"] = ""
            st.session_state["input_ipn"] = ""
            st.rerun()
    else:
        st.write("*Історія порожня*")
