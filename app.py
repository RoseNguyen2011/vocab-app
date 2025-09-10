# app.py - lightweight Streamlit vocab app (stable for Streamlit Cloud)
import streamlit as st
import requests
import pandas as pd
import os
import random
from datetime import datetime, timedelta

DATA_FILE = "vocab_history.csv"
SRS_INTERVALS = [1, 3, 7, 14]  # days for levels 0..3

# --- Data helpers
def ensure_datafile():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=["Word","MeaningVI","Synonyms","ExampleEN","ExampleVI","LastReview","Level"])
        df.to_csv(DATA_FILE, index=False)

def load_data():
    ensure_datafile()
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def fetch_word_from_api(word):
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        j = r.json()
        meaning = j[0]["meanings"][0]["definitions"][0].get("definition","No definition found")
        example = j[0]["meanings"][0]["definitions"][0].get("example","")
        synonyms_list = j[0]["meanings"][0].get("synonyms",[]) or []
        synonyms = ", ".join(synonyms_list) if synonyms_list else ""
        return meaning, example, synonyms
    except Exception:
        return None, None, None

def due_words(df):
    today = datetime.now().date()
    due = []
    for _, row in df.iterrows():
        last = row["LastReview"]
        try:
            last_date = datetime.strptime(str(last), "%Y-%m-%d").date()
        except:
            last_date = datetime.now().date()
        lvl = int(row["Level"]) if not pd.isna(row["Level"]) else 0
        interval = SRS_INTERVALS[min(lvl, 3)]
        if today >= last_date + timedelta(days=interval):
            due.append(row)
    return due

# --- Streamlit UI
st.set_page_config(page_title="Vocab App", layout="centered")
st.title("📚 Vocabulary Learning (Light Version)")

menu = st.sidebar.selectbox("Menu", ["Search & Save", "Daily Review (SRS)", "Flashcard", "Quiz", "Progress"])
df = load_data()

if menu == "Search & Save":
    st.header("Tra cứu từ mới")
    word = st.text_input("Nhập từ tiếng Anh (không dấu):").strip().lower()
    if st.button("Lookup"):
        if not word:
            st.warning("Vui lòng nhập từ.")
        else:
            meaning_en, example_en, synonyms = fetch_word_from_api(word)
            if meaning_en is None:
                st.error("Không tìm thấy từ trên API. Hãy thử từ khác.")
            else:
                st.subheader(f"{word}")
                st.write("**Meaning (EN):**", meaning_en)
                if example_en:
                    st.write("**Example (EN):**", example_en)
                if synonyms:
                    st.write("**Synonyms:**", synonyms)
                # Input Vietnamese meaning (user-entered)
                meaning_vi = st.text_area("Ghi nghĩa tiếng Việt (Bạn có thể nhập/ chỉnh sửa):", height=80)
                if st.button("Save to vocabulary"):
                    today = datetime.now().strftime("%Y-%m-%d")
                    # Append or update
                    if word in df["Word"].values:
                        idx = df.index[df["Word"]==word][0]
                        df.at[idx,"MeaningVI"] = meaning_vi
                        df.at[idx,"Synonyms"] = synonyms
                        df.at[idx,"ExampleEN"] = example_en or ""
                        df.at[idx,"ExampleVI"] = ""
                        df.at[idx,"LastReview"] = today
                        df.at[idx,"Level"] = 0
                        save_data(df)
                        st.success("Đã cập nhật từ trong danh sách.")
                    else:
                        new = {"Word":word,"MeaningVI":meaning_vi,"Synonyms":synonyms,
                               "ExampleEN": example_en or "", "ExampleVI":"", "LastReview": today, "Level":0}
                        df = df.append(new, ignore_index=True)
                        save_data(df)
                        st.success("Đã lưu từ vào danh sách ôn tập.")

elif menu == "Daily Review (SRS)":
    st.header("Daily Review — SRS (1,3,7,14 days)")
    due = due_words(df)
    if not due:
        st.success("🎉 Hôm nay không có từ cần ôn tập.")
    else:
        for i, row in enumerate(due):
            w = row["Word"]
            st.subheader(f"{i+1}. {w}")
            show = st.checkbox(f"Hiện nghĩa {w}", key=f"show_{i}")
            if show:
                st.write("Nghĩa (VI):", row.get("MeaningVI",""))
                st.write("Example (EN):", row.get("ExampleEN",""))
                # Buttons for remember/forget
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Tôi nhớ — {w}", key=f"remember_{i}"):
                        idx = df.index[df["Word"]==w][0]
                        df.at[idx,"LastReview"] = datetime.now().strftime("%Y-%m-%d")
                        df.at[idx,"Level"] = min(int(df.at[idx,"Level"]) + 1, 3)
                        save_data(df)
                        st.success(f"Tăng level cho {w}")
                with col2:
                    if st.button(f"Tôi quên — {w}", key=f"forget_{i}"):
                        idx = df.index[df["Word"]==w][0]
                        df.at[idx,"LastReview"] = datetime.now().strftime("%Y-%m-%d")
                        df.at[idx,"Level"] = 0
                        save_data(df)
                        st.error(f"Reset level cho {w}")

elif menu == "Flashcard":
    st.header("Flashcard — Ôn nhanh")
    if df.empty:
        st.info("Chưa có từ trong danh sách. Vui lòng thêm từ ở Search & Save.")
    else:
        if st.button("Tạo flashcard mới"):
            idx = random.choice(df.index.tolist())
            st.session_state["card_idx"] = idx
            st.session_state["show_ans"] = False
        if "card_idx" in st.session_state:
            idx = st.session_state["card_idx"]
            w = df.at[idx,"Word"]
            st.subheader(w)
            if st.button("Hiện đáp án"):
                st.session_state["show_ans"] = True
            if st.session_state.get("show_ans", False):
                st.write("Nghĩa (VI):", df.at[idx,"MeaningVI"])
                st.write("Example (EN):", df.at[idx,"ExampleEN"])

elif menu == "Quiz":
    st.header("Quiz (Chọn nghĩa đúng)")
    if len(df) < 4:
        st.info("Cần ít nhất 4 từ trong danh sách để làm quiz.")
    else:
        if st.button("Bắt đầu quiz"):
            # choose one word and 3 wrong meanings
            idx = random.choice(df.index.tolist())
            correct = df.at[idx,"MeaningVI"]
            wrongs = []
            while len(wrongs) < 3:
                cand = df.at[random.choice(df.index.tolist()), "MeaningVI"]
                if cand != correct and cand not in wrongs:
                    wrongs.append(cand)
            options = wrongs + [correct]
            random.shuffle(options)
            st.session_state["quiz_word"] = df.at[idx,"Word"]
            st.session_state["quiz_options"] = options
        if "quiz_word" in st.session_state:
            st.write("Từ:", st.session_state["quiz_word"])
            opts = st.session_state["quiz_options"]
            for j,opt in enumerate(opts):
                if st.button(opt, key=f"opt_{j}"):
                    if opt == df[df["Word"]==st.session_state["quiz_word"]].iloc[0]["MeaningVI"]:
                        st.success("✅ Đúng")
                    else:
                        st.error("❌ Sai")

elif menu == "Progress":
    st.header("Progress — Thống kê")
    total = len(df)
    st.write("Tổng số từ:", total)
    if total>0:
        counts = df["Level"].fillna(0).astype(int).value_counts().sort_index()
        st.bar_chart(counts)
        # due today
        st.write("Từ cần ôn hôm nay:", len(due_words(df)))
