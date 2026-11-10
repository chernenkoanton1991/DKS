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

# Ініціалізація історії пошуку та результатів у сесії
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


# --- ШВИДКИЙ ПОТОКОВИЙ ПОШУК (БЕЗ ПЕРЕВАНТАЖЕННЯ ПАМ'ЯТІ) ---
def execute_fast_search(pib_query, dr_query, ipn_query):
    all_files = glob.glob("chunks/chunk_*.csv")
    if not all_files:
        st.error("Помилка: папка 'chunks' порожня або не знайдена.")
        return []

    matched_records = []

    pib_norm = normalize_string(pib_query) if pib_query.strip() else ""
    dr_norm = normalize_string(dr_query) if dr_query.strip() else ""
    ipn_norm = normalize_string(ipn_query) if ipn_query.strip() else ""

    # Почергово скануємо кожен невеликий файл
    for f in all_files:
        chunk = pd.read_csv(f, dtype=str, sep=";")
        chunk = chunk.fillna("—")
        chunk = chunk.replace(r"^\s*$", "—", regex=True)

        # Конвертуємо поточний шматок у список словників для швидкого перебору в ОЗУ
        for row in chunk.to_dict(orient="records"):
            if pib_norm and pib_norm not in normalize_string(
                row.get("Прізвище, імя, по батькові в/с", "")
            ):
                continue
            if dr_norm and dr_norm not in normalize_string(
                row.get("Дата народження", "")
            ):
                continue
            if ipn_norm and ipn_norm not in normalize_string(
                row.get("РНОКПП", "")
            ):
                continue
            matched_records.append(row)

    return matched_records


# --- ІНТЕРФЕЙС ПРОГРАМИ ---
st.title("🔎 Система пошуку по захищеній базі")
st.info(
    "🔒 Система оптимізована. База даних готова до безпечної та стабільної роботи."
)

main_col, history_col = st.columns([3, 1])

with main_col:
    st.markdown("### Введіть дані для пошуку:")
    search_pib = st.text_input("Введіть ПІБ (можна частково):")
    search_dr = st.text_input("Дата народження (напр. 25.12.1985):")
    search_ipn = st.text_input("РНОКПП (ІПН повністю або частина):")

    if st.button("🚀 Запустити пошук", type="primary"):
        if not (search_pib.strip() or search_dr.strip() or search_ipn.strip()):
            st.warning("Будь ласка, заповніть хоча б одне поле для пошуку.")
        else:
            # Фіксація історії
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

            with st.spinner("Проводиться безпечний пошук у базі..."):
                st.session_state["found_entries"] = execute_fast_search(
                    search_pib, search_dr, search_ipn
                )

    # ВІД ОБРАЖЕННЯ РЕЗУЛЬТАТІВ ЗІ СПЛИВАЮЧИМИ КАРТКАМИ ДЕТАЛЕЙ
    if st.session_state["found_entries"] is not None:
        entries = st.session_state["found_entries"]
        st.subheader(f"📊 Знайдено збігів: {len(entries)}")

        if len(entries) > 0:
            display_limit = min(len(entries), 250)

            # Будуємо список карток
            for idx in range(display_limit):
                item = entries[idx]

                pib_val = item.get("Прізвище, імя, по батькові в/с", "—")
                dr_val = item.get("Дата народження", "—")
                ipn_val = item.get("РНОКПП", "—")

                # Створюємо зручний горизонтальний рядок з інтерактивним поповером
                c_text, c_pop = st.columns([4, 1])

                with c_text:
                    st.markdown(
                        f"👤 **{pib_val}** | 📅 ДН: {dr_val} | 📂 РНОКПП: {ipn_val}"
                    )

                with c_pop:
                    # Справжня спливаюча картка деталей, яка не перезавантажує інтерфейс
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
                    "Показано перші 250 результатів. Уточніть пошуковий запит для звуження списку."
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
