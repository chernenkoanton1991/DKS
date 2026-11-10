import base64
import glob
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Пошукова База Даних", layout="wide")

# --- НАЛАШТУВАННЯ ФОНОВИХ ЗОБРАЖЕНЬ ТА КОЛЬОРІВ ---
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        return None

bg_image_base64 = get_base64_image("background.png")

st.markdown(
    """
    <style>
    label, .stWidgetLabel p, h1, h2, h3, h4, h5, h6, .stHeading p, .stMarkdown strong {
        color: #000000 !important;
        font-weight: 700 !important;
    }
    .stMarkdown p, .stText p, li {
        color: #111111 !important;
    }
    div[data-testid="stPopoverBody"], div[data-testid="stPopoverBody"] *, [data-testid="stPopoverBody"] p, [data-testid="stPopoverBody"] span {
        background-color: #fcfcfc !important;
        color: #000000 !important;
        font-weight: 500 !important;
    }
    div[data-testid="stAlert"] {
        background-color: #e3f2fd !important;
        border: 1px solid #90caf9 !important;
    }
    div[data-testid="stAlert"] p, div[data-testid="stAlert"] * {
        color: #0d47a1 !important;
        font-weight: 600 !important;
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
if "secret_question" not in st.session_state:
    st.session_state["secret_question"] = False
if "secret_answer" not in st.session_state:
    st.session_state["secret_answer"] = None

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
            mask &= chunk["Прізвище, імя, по батькові в/с"].astype(str).str.lower().str.contains(pib_norm, case=False, na=False, regex=False)
        if dr_norm:
            mask &= chunk["Дата народження"].astype(str).str.lower().str.contains(dr_norm, case=False, na=False, regex=False)
        if ipn_norm:
            mask &= chunk["РНОКПП"].astype(str).str.lower().str.contains(ipn_norm, case=False, na=False, regex=False)

        filtered_chunk = chunk[mask]
        if not filtered_chunk.empty:
            matched_records.extend(filtered_chunk.to_dict(orient="records"))

    return matched_records

# --- ІНТЕРФЕЙС ПРОГРАМИ ---
st.title("🔎 Система пошуку по захищеній базі")
st.info("⚡ База даних переведена на ультра-швидкий бінарний індекс.")

main_col, history_col = st.columns(2)

with main_col:
    st.markdown("### Введіть дані для пошуку:")

    search_pib = st.text_input("Введіть ПІБ (можна частково):", value=st.session_state["input_pib"])
    search_dr = st.text_input("Дата народження (напр. 25.12.1985):", value=st.session_state["input_dr"])
    search_ipn = st.text_input("РНОКПП (ІПН повністю або частина):", value=st.session_state["input_ipn"])

    if st.button("🚀 Запустити пошук", type="primary"):
        if not (search_pib.strip() or search_dr.strip() or search_ipn.strip()):
            st.warning("Будь ласка, заповніть хоча б одне поле для пошуку.")
        else:
            st.session_state["secret_question"] = False
            st.session_state["secret_answer"] = None
            st.session_state["found_entries"] = None

            clean_pib = normalize_string(search_pib)
            if clean_pib in ["кавецький юрій", "кавецький юрій петрович", "кавецький юрий"]:
                st.session_state["secret_question"] = True
                st.session_state["temp_pib"] = search_pib
                st.session_state["temp_dr"] = search_dr
                st.session_state["temp_ipn"] = search_ipn
            else:
                with st.spinner("Миттєве сканування індексу..."):
                    st.session_state["found_entries"] = execute_fast_feather_search(search_pib, search_dr, search_ipn)

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

            if not st.session_state["search_history"] or st.session_state["search_history"][-1]["text"] != full_text:
                st.session_state["search_history"].append(new_history_item)

    # --- ОБРОБКА ТРИГЕРНОГО ЗАПИТАННЯ ---
    if st.session_state["secret_question"]:
        st.markdown("### ❓ Перевірочне запитання")
        st.warning("🧐 Друг Рубашенка?")
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("👍 Так", type="primary", use_container_width=True):
                st.session_state["secret_question"] = False
                st.session_state["secret_answer"] = "yes"
                with st.spinner("Завантаження деталей..."):
                    st.session_state["found_entries"] = execute_fast_feather_search(st.session_state["temp_pib"], st.session_state["temp_dr"], st.session_state["temp_ipn"])
                st.rerun()
        with col_no:
            if st.button("👎 Ні", type="secondary", use_container_width=True):
                st.session_state["secret_question"] = False
                st.session_state["secret_answer"] = "no"
                st.rerun()

    if st.session_state["secret_answer"] == "no":
        st.markdown("### 📸 Результат перевірки:")
        try:
            st.image("rubashenko.png", caption="Кавецький Юрій Петрович", width=400)
        except Exception:
            st.error("Файл 'rubashenko.png' не знайдено.")

    # --- ВІДОБРАЖЕННЯ РЕЗУЛЬТАТІВ ПОШУКУ ---
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

                c_text, c_pop = st.columns([0.75, 0.25])
                with c_text:
                    st.markdown(f"👤 **{pib_val}** <br>📅 ДН: {dr_val} | 📂 РНОКПП: {ipn_val}", unsafe_allow_html=True)
                with c_pop:
                    with st.popover("📋 Деталі"):
                        st.markdown("### 📋 Повна інформація:")
                        for key, val in item.items():
                            if not key.startswith("_"):
                                st.markdown(f"**{key}:** {val}")
                st.markdown("<hr style='margin:6px 0px; border-top: 1px solid #ccc;'/>", unsafe_allow_html=True)
        else:
            st.warning("Нічого не знайдено за вашим запитом.")

# --- ВІДОБРАЖЕННЯ ІСТОРІЇ ПОШУКУ ---
with history_col:
    st.markdown("### 🕒 Історія пошуку:")
    if st.session_state["search_history"]:
        for h_idx, item in enumerate(reversed(st.session_state["search_history"])):
            btn_key = f"replay_{len(st.session_state['search_history']) - 1 - h_idx}"
            st.write(f"• {item['text']}")
            if st.button("🔄 Повторити цей пошук", key=btn_key):
                st.session_state["secret_question"] = False
                st.session_state["secret_answer"] = None
                st.session_state["input_pib"] = item["pib"]
                st.session_state["input_dr"] = item["dr"]
                st.session_state["input_ipn"] = item["ipn"]

