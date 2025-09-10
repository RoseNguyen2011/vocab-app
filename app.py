import streamlit as st
import requests
from googletrans import Translator
import pandas as pd
import os
from datetime import datetime, timedelta

# ============ CẤU HÌNH ============
DATA_FILE = "vocab_history.csv"
translator = Translator()
intervals = [1, 3, 7, 14]  # spaced repetition

# ============ HÀM XỬ LÝ ============
def load_data():
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame(columns=["Word", "MeaningVI", "Synonyms", "ExampleEN", "ExampleVI", "LastReview", "Level"])
        df.to_csv(DATA_FILE, index=False)
    return pd.read_csv(DATA_FILE)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def get_word_info(word):
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    try:
        res = requests.get(url).json()
        meaning = res[0]["meanings"][0]["definitions"][0]["definition"]
        example = res[0]["meanings"][0]["definitions"][0].get("example", "No example")
        synonyms = ", ".join(res[0]["meanings"][0].get("synonyms", [])) or "None"
    except:
        meaning, example, synonyms = "Not found", "Not found", "None"

    meaning_vi = translator.translate(meaning, src="en", dest="vi").text
    example_vi = translator.translate(example, src="en", dest="vi").text
    return meaning, meaning_vi, synonyms, example, example_vi

def review_due_words(df):
    today = datetime.now().date()
    due_words = []
    for i, row in df.iterrows():
        lvl = int(row["Level"])
        last = datetime.strptime(str(row["LastReview"]), "%Y-%m-%d").date()
        if today >= last + timedelta(days=intervals[min(lvl, 3)]):
            due_words.append(row)
    return due_words

# ============ GIAO DIỆN ============
st.set_page_config(page_title="Vocabulary Learning App", layout="centered")

st.title("📘 Ứng dụng học từ vựng tiếng Anh")
st.write("Học từ mới, ôn tập bằng SRS (1–3–7–14 ngày), theo dõi tiến độ 📊")

menu = st.sidebar.radio("Chọn chức năng", ["Tra cứu từ mới", "Ôn tập (SRS)", "Tiến độ học tập"])

df = load_data()

# ---------- TRA CỨU ----------
if menu == "Tra cứu từ mới":
    word = st.text_input("Nhập từ tiếng Anh:")
    if st.button("Tra cứu"):
        if word:
            meaning_en, meaning_vi, synonyms, example_en, example_vi = get_word_info(word)

            st.subheader(f"👉 {word}")
            st.write(f"**Nghĩa (EN):** {meaning_en}")
            st.write(f"**Nghĩa (VI):** {meaning_vi}")
            st.write(f"**Từ đồng nghĩa:** {synonyms}")
            st.write(f"**Ví dụ (EN):** {example_en}")
            st.write(f"**Ví dụ (VI):** {example_vi}")

            # Lưu vào dữ liệu
            today = datetime.now().strftime("%Y-%m-%d")
            if word not in df["Word"].values:
                new_row = pd.DataFrame([[word, meaning_vi, synonyms, example_en, example_vi, today, 0]],
                                       columns=df.columns)
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df)
                st.success("✅ Đã lưu vào danh sách ôn tập")

# ---------- ÔN TẬP ----------
elif menu == "Ôn tập (SRS)":
    due_words = review_due_words(df)
    if not due_words:
        st.success("🎉 Hôm nay không có từ nào cần ôn tập")
    else:
        for _, row in pd.DataFrame(due_words).iterrows():
            st.subheader(f"👉 {row['Word']}")
            if st.button(f"Hiện đáp án cho {row['Word']}"):
                st.write(f"**Nghĩa (VI):** {row['MeaningVI']}")
                st.write(f"**Ví dụ (EN):** {row['ExampleEN']}")
                st.write(f"**Ví dụ (VI):** {row['ExampleVI']}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Tôi nhớ {row['Word']}"):
                    idx = df[df["Word"] == row["Word"]].index[0]
                    df.at[idx, "Level"] = min(int(row["Level"]) + 1, 3)
                    df.at[idx, "LastReview"] = datetime.now().strftime("%Y-%m-%d")
                    save_data(df)
                    st.success("👍 Tăng level")
            with col2:
                if st.button(f"Tôi quên {row['Word']}"):
                    idx = df[df["Word"] == row["Word"]].index[0]
                    df.at[idx, "Level"] = 0
                    df.at[idx, "LastReview"] = datetime.now().strftime("%Y-%m-%d")
                    save_data(df)
                    st.error("🔄 Reset về level 0")

# ---------- TIẾN ĐỘ ----------
elif menu == "Tiến độ học tập":
    st.subheader("📊 Thống kê học tập")
    total = len(df)
    levels = df["Level"].value_counts().to_dict()
    due_today = len(review_due_words(df))

    st.write(f"- Tổng số từ đã lưu: **{total}**")
    st.write(f"- Level 0 (Mới/Quên): {levels.get(0,0)}")
    st.write(f"- Level 1 (Ôn 1 ngày): {levels.get(1,0)}")
    st.write(f"- Level 2 (Ôn 3 ngày): {levels.get(2,0)}")
    st.write(f"- Level 3 (Ôn 7–14 ngày): {levels.get(3,0)}")
    st.write(f"- 📌 Từ cần ôn hôm nay: **{due_today}**")

    if total > 0:
        st.bar_chart(df["Level"].value_counts())
