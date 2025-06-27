import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import traceback

st.set_page_config(page_title="ฟอร์มประเมินผู้เข้าสอบปี 2567", layout="wide")
st.title("ฟอร์มประเมินผู้เข้าสอบปี 2567")

# เชื่อม Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"]
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

# โหลดข้อมูลคะแนนเดิม
def get_existing_data(sheet, exam_id, committee_id):
    df = pd.DataFrame(sheet.get_all_records())
    df.columns = df.columns.astype(str).str.strip().str.lower()
    match = df[(df["exam_id"] == exam_id) & (df["committee_id"] == committee_id)]
    return match.iloc[0] if not match.empty else None

# ----------------- ฟอร์มข้อมูลทั่วไป -----------------
col1, col2, col3 = st.columns(3)
with col1:
    exam_id = st.selectbox("เลือกเลขประจำตัวสอบ", list(exam_dict.keys()))
with col2:
    committee_id = st.selectbox("กรรมการคนที่", ["1", "2", "3"])
with col3:
    exam_date = st.date_input("วันที่สอบ", datetime.today())

# ดึงข้อมูลจากไฟล์ CSV
default_name, default_time = exam_dict.get(exam_id, ("", ""))

# โหลดข้อมูลเก่าจาก Google Sheets ถ้ามี
existing = get_existing_data(sheet, exam_id, committee_id)

# ค่าเริ่มต้น
initial_scores = {}
if existing is not None:
    default_name = existing["name"]
    default_time = existing["time"]
    initial_scores = {
        "1.1 ท่าทางสง่า": existing["sum1"] // 4,
        "1.2 สะอาดเรียบร้อย": existing["sum1"] // 4,
        "1.3 เคารพ": existing["sum1"] // 4,
        "1.4 ควบคุมอารมณ์": existing["sum1"] - 3 * (existing["sum1"] // 4),
        "2.1 ตอบเร็ว": existing["sum2"] // 4,
        "2.2 เหมาะสม": existing["sum2"] // 4,
        "2.3 มั่นใจ": existing["sum2"] // 4,
        "2.4 เข้าใจง่าย": existing["sum2"] - 3 * (existing["sum2"] // 4),
        "3.1 ตรงคำถาม": existing["sum3"] // 4,
        "3.2 จากประสบการณ์": existing["sum3"] // 4,
        "3.3 มีเหตุผล": existing["sum3"] // 4,
        "3.4 ใช้ภาษาเหมาะสม": existing["sum3"] - 3 * (existing["sum3"] // 4),
        "4.1 คิดเชิงระบบ": existing["sum4"] // 3,
        "4.2 มีเป้าหมาย": existing["sum4"] // 3,
        "4.3 วางแผนดี": existing["sum4"] - 2 * (existing["sum4"] // 3),
        "5.1 รู้เรื่องกองทัพ": existing["sum5"] // 3,
        "5.2 ทัศนคติดี": existing["sum5"] // 3,
        "5.3 มีจริยธรรม": existing["sum5"] - 2 * (existing["sum5"] // 3),
    }

col4, col5 = st.columns(2)
with col4:
    name = st.text_input("ชื่อผู้เข้าสอบ", value=default_name)
with col5:
    time = st.text_input("เวลาสอบ", value=default_time)

st.divider()
st.subheader("กรุณาให้คะแนนแต่ละหัวข้อ (0 - 5)")

# ฟังก์ชันรวมคะแนนจาก radio button
def radio_group(title, questions):
    st.markdown(f"### {title}")
    total = 0
    for q in questions:
        key = f"{exam_id}_{committee_id}_{q}"
        score = st.radio(q, [0, 1, 2, 3, 4, 5], horizontal=True, key=key, index=initial_scores.get(q, 0))
        total += score
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

comment = st.text_area("ความคิดเห็นเพิ่มเติม", value=existing["comment"] if existing is not None else "")

# บันทึกข้อมูล
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
        st.success("✅ บันทึกคะแนนเรียบร้อยแล้วใน Google Sheets!")

    st.session_state.clear()
    st.experimental_rerun()
