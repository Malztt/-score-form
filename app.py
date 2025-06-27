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

# โหลดชีต
@st.cache_data
def get_worksheet(sheet_id: str, worksheet_name: str = "A1"):
    spreadsheet = client.open_by_key(sheet_id)
    worksheet = spreadsheet.worksheet(worksheet_name)
    return worksheet

# โหลดข้อมูลจากชีต (แก้ param เป็น _sheet เพื่อไม่ให้ Streamlit hash มัน)
@st.cache_data
def load_all_records(_sheet):
    return _sheet.get_all_records()

@st.cache_data
def load_all_values(_sheet):
    return _sheet.get_all_values()

@st.cache_data
def load_exam_data():
    return pd.read_csv("exam_schedule.csv", dtype=str)

SHEET_ID = "16QNx4xaRjgvPnimZvS5nVA8HPcDTWg98QXKnCgWa7Xw"
SHEET_NAME = "A1"

try:
    sheet = get_worksheet(SHEET_ID, SHEET_NAME)
    records = load_all_records(sheet)
    all_values = load_all_values(sheet)
    st.success("✅ เชื่อมต่อ Google Sheets สำเร็จ")
except Exception:
    st.error("❌ ไม่สามารถโหลด Google Sheets ได้")
    st.code(traceback.format_exc())
    st.stop()

# ----------------------------
data = load_exam_data()
exam_dict = dict(zip(data["exam_id"], zip(data["name"], data["time"])))

col1, col2, col3 = st.columns(3)
with col1:
    exam_id = st.selectbox("เลือกเลขประจำตัวสอบ", list(exam_dict.keys()))
with col2:
    committee_id = st.selectbox("กรรมการคนที่", ["1", "2", "3"])
with col3:
    exam_date = st.date_input("วันที่สอบ", datetime.today())

def reset_form():
    for k in list(st.session_state.keys()):
        if k.startswith(("1.", "2.", "3.", "4.", "5.")) or k in ["comment", "confirm_edit"]:
            del st.session_state[k]

if "last_exam_id" not in st.session_state:
    st.session_state.last_exam_id = exam_id
if "last_committee_id" not in st.session_state:
    st.session_state.last_committee_id = committee_id

if exam_id != st.session_state.last_exam_id or committee_id != st.session_state.last_committee_id:
    reset_form()
    st.session_state.last_exam_id = exam_id
    st.session_state.last_committee_id = committee_id

default_name, default_time = exam_dict.get(exam_id, ("", ""))
col4, col5 = st.columns(2)
with col4:
    name = st.text_input("ชื่อผู้เข้าสอบ", value=default_name)
with col5:
    time = st.text_input("เวลาสอบ", value=default_time)

st.divider()
st.subheader("กรุณาให้คะแนนแต่ละหัวข้อ (0 - 5)")

score_keys = [
    "1.1 ท่าทางสง่า", "1.2 สะอาดเรียบร้อย", "1.3 เคารพ", "1.4 ควบคุมอารมณ์",
    "2.1 ตอบเร็ว", "2.2 เหมาะสม", "2.3 มั่นใจ", "2.4 เข้าใจง่าย",
    "3.1 ตรงคำถาม", "3.2 จากประสบการณ์", "3.3 มีเหตุผล", "3.4 ใช้ภาษาเหมาะสม",
    "4.1 คิดเชิงระบบ", "4.2 มีเป้าหมาย", "4.3 วางแผนดี",
    "5.1 รู้เรื่องกองทัพ", "5.2 ทัศนคติดี", "5.3 มีจริยธรรม"
]

def find_existing_row():
    for i, row in enumerate(records, start=2):
        if str(row.get("exam_id", "")) == exam_id and str(row.get("committee_id", "")) == committee_id:
            return i
    return None

existing_row = find_existing_row()
existing_data = []

if existing_row:
    existing_data = all_values[existing_row - 1]
    try:
        scores = list(map(int, existing_data[5:5+18]))
        for k, v in zip(score_keys, scores):
            st.session_state[k] = v
        st.session_state["comment"] = existing_data[12]
        st.info("⚠️ พบข้อมูลเดิม กำลังโหลดขึ้นมา")
    except:
        st.warning("⚠️ โหลดข้อมูลเก่าไม่สำเร็จ")

def radio_group(title, keys):
    st.markdown(f"### {title}")
    total = 0
    for q in keys:
        score = st.radio(q, [0, 1, 2, 3, 4, 5],
                         horizontal=True, index=st.session_state.get(q, 0), key=q)
        total += score
    return total

sum1 = radio_group("1. ลักษณะท่าทางและระเบียบวินัย", score_keys[0:4])
sum2 = radio_group("2. ปฏิกิริยาไหวพริบ", score_keys[4:8])
sum3 = radio_group("3. การใช้ความรู้", score_keys[8:12])
sum4 = radio_group("4. ประสบการณ์", score_keys[12:15])
sum5 = radio_group("5. วิชาทหาร/คุณธรรม", score_keys[15:18])
total_score = sum1 + sum2 + sum3 + sum4 + sum5
st.success(f"คะแนนรวมทั้งหมด: {total_score} คะแนน")

comment = st.text_area("ความคิดเห็นเพิ่มเติม", value=st.session_state.get("comment", ""), key="comment")

def has_unscored_questions():
    return any(st.session_state.get(k, 0) == 0 for k in score_keys)

confirm_edit = True
if existing_row and len(existing_data) >= 13:
    old_scores = list(map(int, existing_data[5:5+18]))
    current_scores = [st.session_state.get(k, 0) for k in score_keys]
    old_comment = existing_data[12]
    if old_scores != current_scores or old_comment != st.session_state.get("comment", ""):
        confirm_edit = st.checkbox("ยืนยันว่าต้องการแก้ไขข้อมูลเดิม", key="confirm_edit")
        st.warning("⚠️ คุณกำลังจะแก้ไขข้อมูลเดิม กรุณายืนยันก่อนบันทึก")

if st.button("บันทึกคะแนน"):
    if has_unscored_questions():
        st.error("❌ กรุณาให้คะแนนทุกข้อก่อนบันทึก")
    elif existing_row and not confirm_edit:
        st.warning("⚠️ กรุณาติ๊กยืนยันว่าต้องการแก้ไขข้อมูลเดิมก่อน")
    else:
        new_row = [
            exam_id, committee_id, name,
            exam_date.strftime('%Y-%m-%d'), time,
            sum1, sum2, sum3, sum4, sum5,
            total_score, st.session_state.get("comment", "")
        ]

try:
    if existing_row:
        sheet.update(f"A{existing_row}:M{existing_row}", [new_row])
        st.success("✅ อัปเดตคะแนนเรียบร้อยแล้วใน Google Sheets!")
    else:
        # ป้องกัน error จาก gspread/authorized session conflict
        sheet.insert_row(new_row, index=len(all_values) + 1)
        st.success("✅ บันทึกคะแนนเรียบร้อยแล้วที่ Google Sheets!")
    st.cache_data.clear()

        except Exception as e:
            st.error("❌ เกิดข้อผิดพลาดระหว่างบันทึก")
            st.code(traceback.format_exc())
