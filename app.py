import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import traceback

st.set_page_config(page_title="ฟอร์มประเมินผู้เข้าสอบปี 2567", layout="wide")
st.title("ฟอร์มประเมินผู้เข้าสอบปี 2567")

# เชื่อม Google Sheets
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scope
)
client = gspread.authorize(creds)

try:
    spreadsheet = client.open_by_key("16QNx4xaRjgvPnimZvS5nVA8HPcDTWg98QXKnCgWa7Xw")
    sheet = spreadsheet.worksheet("A1")
    st.success("✅ เชื่อมต่อ Google Sheets ได้สำเร็จ")
except Exception as e:
    st.error("❌ ไม่สามารถเชื่อม Google Sheets ได้:")
    st.code(traceback.format_exc())
    st.stop()

# โหลดข้อมูลจาก CSV
@st.cache_data
def load_exam_data():
    return pd.read_csv("exam_schedule.csv", dtype=str)

data = load_exam_data()
exam_dict = dict(zip(data["exam_id"], zip(data["name"], data["time"])))

# ===== ฟังก์ชัน =====
def find_existing_row(sheet, exam_id, committee_id):
    records = sheet.get_all_records()
    for i, row in enumerate(records, start=2):
        if str(row.get("exam_id", "")).strip() == str(exam_id) and str(row.get("committee_id", "")).strip() == str(committee_id):
            return i
    return None

def get_existing_data(sheet, exam_id, committee_id):
    df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.astype(str).str.strip()
    match = df[(df["exam_id"].astype(str) == exam_id) & (df["committee_id"].astype(str) == committee_id)]
    if not match.empty:
        return match.iloc[0].to_dict()
    return {}

# ===== ฟอร์มข้อมูลทั่วไป =====
col1, col2, col3 = st.columns(3)
with col1:
    exam_id = st.selectbox("เลือกเลขประจำตัวสอบ", list(exam_dict.keys()))
with col2:
    committee_id = st.selectbox("กรรมการคนที่", ["1", "2", "3"])
with col3:
    exam_date = st.date_input("วันที่สอบ", datetime.today())

default_name, default_time = exam_dict.get(exam_id, ("", ""))
existing_data = get_existing_data(sheet, exam_id, committee_id)

col4, col5 = st.columns(2)
with col4:
    name = st.text_input("ชื่อผู้เข้าสอบ", value=existing_data.get("name", default_name))
with col5:
    time = st.text_input("เวลาสอบ", value=existing_data.get("time", default_time))

st.divider()
st.subheader("กรุณาให้คะแนนแต่ละหัวข้อ (0 - 5)")

# ===== การประเมินคะแนน =====
def radio_group(title, questions):
    st.markdown(f"### {title}")
    total = 0
    for q in questions:
        key = f"{q}_{exam_id}_{committee_id}"
        score = st.radio(
            q,
            [0, 1, 2, 3, 4, 5],
            horizontal=True,
            index=existing_data.get(q, 0) if isinstance(existing_data.get(q), int) else 0,
            key=key
        )
        total += score
        st.session_state[key] = score
    return total

sum1 = radio_group("1. ลักษณะท่าทางและระเบียบวินัย", [
    "1.1 ท่าทางสง่า", "1.2 สะอาดเรียบร้อย", "1.3 เคารพ", "1.4 ควบคุมอารมณ์"])
sum2 = radio_group("2. ปฏิกิริยาไหวพริบ", [
    "2.1 ตอบเร็ว", "2.2 เหมาะสม", "2.3 มั่นใจ", "2.4 เข้าใจง่าย"])
sum3 = radio_group("3. การใช้ความรู้", [
    "3.1 ตรงคำถาม", "3.2 จากประสบการณ์", "3.3 มีเหตุผล", "3.4 ใช้ภาษาเหมาะสม"])
sum4 = radio_group("4. ประสบการณ์", [
    "4.1 คิดเชิงระบบ", "4.2 มีเป้าหมาย", "4.3 วางแผนดี"])
sum5 = radio_group("5. วิชาทหาร/คุณธรรม", [
    "5.1 รู้เรื่องกองทัพ", "5.2 ทัศนคติดี", "5.3 มีจริยธรรม"])

total_score = sum1 + sum2 + sum3 + sum4 + sum5
st.success(f"คะแนนรวมทั้งหมด: {total_score} คะแนน")

comment = st.text_area("ความคิดเห็นเพิ่มเติม", value=existing_data.get("comment", ""))

# ===== บันทึกหรืออัปเดต =====
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

    # Reset radio fields
    for k in list(st.session_state.keys()):
        if exam_id in k and committee_id in k:
            del st.session_state[k]
    st.experimental_rerun()
