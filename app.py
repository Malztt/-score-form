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
    st.success("✅ เชื่อมต่อ Google Sheets ได้สำเร็จ")
    sheet = spreadsheet.worksheet("A1")  # หรือ .sheet1 ถ้าใช้ default sheet
except Exception as e:
    st.error("❌ ไม่สามารถเชื่อม Google Sheets ได้:")
    st.code(traceback.format_exc())  # แสดงข้อความ error แบบเต็ม
    st.stop()

# ข้อมูลทั่วไป
col1, col2, col3 = st.columns(3)
with col1:
    exam_id = st.selectbox("เลือกเลขประจำตัวสอบ", ["8013100001", "8013100002", "8013100003", "8013100004"])
with col2:
    committee_id = st.selectbox("กรรมการคนที่", ["1", "2", "3"])
with col3:
    exam_date = st.date_input("วันที่สอบ", datetime.today())

col4, col5 = st.columns(2)
with col4:
    name = st.text_input("ชื่อผู้เข้าสอบ")
with col5:
    time = st.text_input("เวลาสอบ", placeholder="เช่น 09:00 - 09:20")

st.divider()
st.subheader("กรุณาให้คะแนนแต่ละหัวข้อ (0 - 5)")

# ===== หัวข้อการประเมิน (ย่อเพื่อความกระชับ) =====
def slider_group(title, sliders):
    st.markdown(f"### {title}")
    return sum([st.slider(q, 0, 5) for q in sliders])

sum1 = slider_group("1. ลักษณะท่าทางและระเบียบวินัย", [
    "1.1 ท่าทางสง่า", "1.2 สะอาดเรียบร้อย", "1.3 เคารพ", "1.4 ควบคุมอารมณ์"])
sum2 = slider_group("2. ปฏิกิริยาไหวพริบ", [
    "2.1 ตอบเร็ว", "2.2 เหมาะสม", "2.3 มั่นใจ", "2.4 เข้าใจง่าย"])
sum3 = slider_group("3. การใช้ความรู้", [
    "3.1 ตรงคำถาม", "3.2 จากประสบการณ์", "3.3 มีเหตุผล", "3.4 ใช้ภาษาเหมาะสม"])
sum4 = slider_group("4. ประสบการณ์", [
    "4.1 คิดเชิงระบบ", "4.2 มีเป้าหมาย", "4.3 วางแผนดี"])
sum5 = slider_group("5. วิชาทหาร/คุณธรรม", [
    "5.1 รู้เรื่องกองทัพ", "5.2 ทัศนคติดี", "5.3 มีจริยธรรม"])

total_score = sum1 + sum2 + sum3 + sum4 + sum5
st.success(f"คะแนนรวมทั้งหมด: {total_score} คะแนน")

comment = st.text_area("ความคิดเห็นเพิ่มเติม", "")

if st.button("บันทึกคะแนน"):
    new_row = [
        exam_id, committee_id, name,
        exam_date.strftime('%Y-%m-%d'), time,
        sum1, sum2, sum3, sum4, sum5,
        total_score, comment
    ]
    sheet.append_row(new_row)
    st.success("✅ บันทึกคะแนนเรียบร้อยแล้วที่ Google Sheets!")
