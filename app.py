import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import traceback

st.set_page_config(page_title="ฟอร์มประเมินผู้เข้าสอบปี 2567", layout="wide")
st.title("ฟอร์มประเมินผู้เข้าสอบปี 2567")

# ================== CONNECT GOOGLE SHEET ====================
scope = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scope
)
client = gspread.authorize(creds)

try:
    spreadsheet = client.open_by_key("16QNx4xaRjgvPnimZvS5nVA8HPcDTWg98QXKnCgWa7Xw")
    st.success("✅ เชื่อมต่อ Google Sheets ได้สำเร็จ")
    sheet = spreadsheet.worksheet("A1")
except Exception:
    st.error("❌ ไม่สามารถเชื่อม Google Sheets ได้:")
    st.code(traceback.format_exc())
    st.stop()

# ================== CANDIDATE CSV ====================
@st.cache_data
def load_exam_data():
    return pd.read_csv("exam_schedule.csv", dtype=str)

data = load_exam_data()
exam_dict = dict(zip(data["exam_id"], zip(data["name"], data["time"])))

# ================== LOAD EXISTING SCORES ====================
@st.cache_data(ttl=60)
def load_existing_scores():
    return pd.DataFrame(sheet.get_all_records())

existing_df = load_existing_scores()

def get_existing_data(exam_id, committee_id):
    match = existing_df[
        (existing_df["exam_id"] == exam_id) & (existing_df["committee_id"] == committee_id)
    ]
    return match.iloc[0] if not match.empty else None

# ================== FORM HEADER ====================
col1, col2, col3 = st.columns(3)
with col1:
    exam_id = st.selectbox("เลือกเลขประจำตัวสอบ", list(exam_dict.keys()))
with col2:
    committee_id = st.selectbox("กรรมการคนที่", ["1", "2", "3"])
with col3:
    exam_date = st.date_input("วันที่สอบ", datetime.today())

default_name, default_time = exam_dict.get(exam_id, ("", ""))
existing = get_existing_data(exam_id, committee_id)

col4, col5 = st.columns(2)
with col4:
    name = st.text_input("ชื่อผู้เข้าสอบ", value=default_name)
with col5:
    time = st.text_input("เวลาสอบ", value=default_time)

# ================== RADIO INPUTS ====================
st.divider()
st.subheader("กรุณาให้คะแนนแต่ละหัวข้อ (0 - 5)")

# ดึงค่าที่เคยกรอกไว้ ถ้ามี
preload_scores = {}
if existing is not None:
    for i in range(1, 6):
        preload_scores[f"sum{i}"] = existing.get(f"sum{i}", 0)
    preload_comment = existing.get("comment", "")
else:
    preload_scores = {f"sum{i}": 0 for i in range(1, 6)}
    preload_comment = ""

def radio_group(title, questions, group_key, base_index):
    st.markdown(f"### {title}")
    total = 0
    for i, q in enumerate(questions):
        key = f"{group_key}_{i}"
        score = st.radio(q, [0, 1, 2, 3, 4, 5],
                         horizontal=True,
                         index=0,
                         key=key)
        total += score
    return total

sum1 = radio_group("1. ลักษณะท่าทางและระเบียบวินัย",
                   ["1.1 ท่าทางสง่า", "1.2 สะอาดเรียบร้อย", "1.3 เคารพ", "1.4 ควบคุมอารมณ์"], "g1", 0)
sum2 = radio_group("2. ปฏิกิริยาไหวพริบ",
                   ["2.1 ตอบเร็ว", "2.2 เหมาะสม", "2.3 มั่นใจ", "2.4 เข้าใจง่าย"], "g2", 4)
sum3 = radio_group("3. การใช้ความรู้",
                   ["3.1 ตรงคำถาม", "3.2 จากประสบการณ์", "3.3 มีเหตุผล", "3.4 ใช้ภาษาเหมาะสม"], "g3", 8)
sum4 = radio_group("4. ประสบการณ์",
                   ["4.1 คิดเชิงระบบ", "4.2 มีเป้าหมาย", "4.3 วางแผนดี"], "g4", 12)
sum5 = radio_group("5. วิชาทหาร/คุณธรรม",
                   ["5.1 รู้เรื่องกองทัพ", "5.2 ทัศนคติดี", "5.3 มีจริยธรรม"], "g5", 15)

total_score = sum1 + sum2 + sum3 + sum4 + sum5
st.success(f"คะแนนรวมทั้งหมด: {total_score} คะแนน")

comment = st.text_area("ความคิดเห็นเพิ่มเติม", value=preload_comment, key="comment_box")

# ================== SAVE TO SHEET ====================
def find_existing_row(sheet, exam_id, committee_id):
    records = sheet.get_all_records()
    for i, row in enumerate(records, start=2):
        if str(row.get("exam_id", "")) == exam_id and str(row.get("committee_id", "")) == committee_id:
            return i
    return None

if st.button("บันทึกคะแนน"):
    new_row = [
        exam_id, committee_id, name,
        exam_date.strftime('%Y-%m-%d'), time,
        sum1, sum2, sum3, sum4, sum5,
        total_score, comment
    ]

    existing_row = find_existing_row(sheet, exam_id, committee_id)
    if existing_row:
        sheet.update(f"A{existing_row}:M{existing_row}", [new_row])
        st.success("✅ อัปเดตคะแนนเรียบร้อยแล้วใน Google Sheets!")
    else:
        sheet.append_row(new_row)
        st.success("✅ บันทึกคะแนนเรียบร้อยแล้วที่ Google Sheets!")

    # รีเซต session state หลังบันทึก
    for k in st.session_state.keys():
        if k.startswith("g"):
            st.session_state[k] = 0
    st.session_state["comment_box"] = ""
