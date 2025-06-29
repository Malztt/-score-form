import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import traceback

st.set_page_config(page_title="ฟอร์มประเมินผู้เข้าสอบปี 2567", layout="wide")
st.title("ฟอร์มประเมินผู้เข้าสอบปี 2567")

SPREADSHEET_KEY = "16QNx4xaRjgvPnimZvS5nVA8HPcDTWg98QXKnCgWa7Xw"
WORKSHEET_NAME = "A1"

# ฟังก์ชันเชื่อม Google Sheets
def connect_sheet():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scope
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SPREADSHEET_KEY)
        return spreadsheet.worksheet(WORKSHEET_NAME)
    except Exception as e:
        st.error("❌ ไม่สามารถเชื่อม Google Sheets ได้:")
        st.code(traceback.format_exc())
        st.stop()

sheet = connect_sheet()
st.success("✅ เชื่อมต่อ Google Sheets ได้สำเร็จ")

# โหลดข้อมูลจาก Sheet (Cache 5 นาที)
@st.cache_data(ttl=300)
def load_existing_records():
    try:
        sheet_cached = connect_sheet()
        return sheet_cached.get_all_records()
    except Exception as e:
        st.warning("⚠️ โหลดข้อมูลเก่าล้มเหลว (แต่อาจยังเขียนได้)")
        return []

# ค้นหาแถวที่มีข้อมูลเดิม
def find_existing_row(records, exam_id, committee_id):
    for i, row in enumerate(records, start=2):  # row 1 เป็น header
        if str(row.get("exam_id", "")) == exam_id and str(row.get("committee_id", "")) == committee_id:
            return i
    return None

# โหลดตารางสอบจาก CSV
@st.cache_data
def load_exam_data():
    return pd.read_csv("exam_schedule.csv", dtype=str)

data = load_exam_data()
exam_dict = dict(zip(data["exam_id"], zip(data["name"], data["time"])))

# ===== ฟอร์มข้อมูลทั่วไป =====
col1, col2, col3 = st.columns(3)
with col1:
    exam_id = st.selectbox("เลือกเลขประจำตัวสอบ", list(exam_dict.keys()))
with col2:
    committee_id = st.selectbox("กรรมการคนที่", ["1", "2", "3"])
with col3:
    exam_date = st.date_input("วันที่สอบ", datetime.today())

default_name, default_time = exam_dict.get(exam_id, ("", ""))
col4, col5 = st.columns(2)
with col4:
    name = st.text_input("ชื่อผู้เข้าสอบ", value=default_name)
with col5:
    time = st.text_input("เวลาสอบ", value=default_time)

st.divider()
st.subheader("กรุณาให้คะแนนแต่ละหัวข้อ (0 - 5)")

# ===== แบบประเมิน =====
def radio_group(title, questions):
    st.markdown(f"### {title}")
    total = 0
    for q in questions:
        score = st.radio(q, [0, 1, 2, 3, 4, 5], horizontal=True, index=0, key=q)
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

comment = st.text_area("ความคิดเห็นเพิ่มเติม", "")

# ===== ตรวจสอบข้อมูลซ้ำ =====
records = load_existing_records()
existing_row = find_existing_row(records, exam_id, committee_id)
confirm_update = None

if existing_row:
    st.warning("⚠️ มีการบันทึกคะแนนสำหรับเลขประจำตัวสอบนี้แล้วโดยกรรมการคนนี้")
    confirm_update = st.radio(
        "คุณต้องการอัปเดตคะแนนเดิมหรือไม่?",
        ["ไม่", "ใช่"],
        horizontal=True,
        key="confirm_update_radio"
    )

# ===== บันทึกข้อมูล =====
if st.button("บันทึกคะแนน"):
    new_row = [
        exam_id, committee_id, name,
        exam_date.strftime('%Y-%m-%d'), time,
        sum1, sum2, sum3, sum4, sum5,
        total_score, comment
    ]

    try:
        if existing_row and confirm_update == "ใช่":
            sheet.update(f"A{existing_row}:M{existing_row}", [new_row])
            st.success("✅ อัปเดตคะแนนเรียบร้อยแล้วใน Google Sheets!")
            st.toast("อัปเดตข้อมูลสำเร็จ", icon="🔄")
            st.balloons()
        elif not existing_row:
            sheet.append_row(new_row)
            st.success("✅ บันทึกคะแนนเรียบร้อยแล้วที่ Google Sheets!")
            st.toast("บันทึกข้อมูลใหม่สำเร็จ", icon="📥")
            st.balloons()
        else:
            st.info("ℹ️ ยกเลิกการอัปเดตคะแนน")
    except Exception as e:
        st.error("❌ เกิดข้อผิดพลาดระหว่างบันทึกข้อมูล")
        st.code(traceback.format_exc())
