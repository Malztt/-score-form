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

# ---------- CONNECT TO GOOGLE SHEET ----------
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

# ---------- CACHE EXISTING RECORDS ----------
@st.cache_data(ttl=300)
def load_existing_records():
    try:
        sheet_cached = connect_sheet()
        return sheet_cached.get_all_records()
    except Exception:
        return []

# ---------- LOAD EXAM CSV ----------
@st.cache_data
def load_exam_data():
    return pd.read_csv("exam_schedule.csv", dtype=str)

data = load_exam_data()
exam_dict = dict(zip(data["exam_id"], zip(data["name"], data["time"])))

# ---------- NEW EVALUATION QUESTIONS ----------
all_questions = [
    "1.1 บุคลิกภาพ, รูปร่างเหมาะสม", "1.2 การวางตัวเหมาะสม", "1.3 การใช้คำพูด ชัดเจน", "1.4 ความถูกต้องของภาษาพูด",
    "2.1 ตอบคำถามได้รวดเร็ว", "2.2 ตอบคำถามได้เหมาะสม", "2.3 แสดงความมั่นใจในการตอบคำถาม", "2.4 การแก้ไขปัญหาเฉพาะหน้า",
    "3.1 การใช้หลักวิชาการแก้ปัญหา", "3.2 มีความเข้าใจงานที่ต้องทำ และมีแนวทางพัฒนา", 
    "3.3 มีความรอบรู้เกี่ยวกับสังคมไทย สังคมโลก และกองทัพอากาศ", "3.4 มีความสนใจติดตามข่าวสารและเทคโนโลยีสารสนเทศ",
    "4.1 มีวิธีคิดของตนเองอย่างเป็นระบบ", "4.2 มีเป้าหมายในการดำเนินชีวิต", 
    "4.3 มีการกำหนดเป้าหมายในการทำงาน", "4.4 แสดงความภูมิใจในตนเอง/ครอบครัว",
    "5.1 มีค่านิยมและทัศนคติที่ดีต่อการเป็นทหาร", "5.2 การยอมรับกฎเกณฑ์และการปฏิบัติตามคำสั่ง", 
    "5.3 มีความสามารถในการควบคุมอารมณ์", "5.4 มีการจัดการกับอารมณ์ของตนเองอย่างเหมาะสม"
]

# ---------- FORM SECTION ----------
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

# ---------- LOAD SCORES OR RESET ----------
records = load_existing_records()
record = next(
    (r for r in records if str(r.get("exam_id")) == exam_id and str(r.get("committee_id")) == committee_id),
    None
)

def load_scores_to_session(record):
    for q in all_questions:
        if q not in st.session_state:
            try:
                st.session_state[q] = int(record.get(q, 0))
            except:
                st.session_state[q] = 0
    if "comment" not in st.session_state:
        st.session_state["comment"] = record.get("comment", "")

def clear_scores_session_state():
    for q in all_questions:
        st.session_state[q] = 0
    st.session_state["comment"] = ""

# เช็คและเคลียร์ session_state เมื่อเปลี่ยน exam_id หรือ committee_id
if "prev_exam_id" not in st.session_state:
    st.session_state["prev_exam_id"] = None
if "prev_committee_id" not in st.session_state:
    st.session_state["prev_committee_id"] = None

if (st.session_state["prev_exam_id"] != exam_id) or (st.session_state["prev_committee_id"] != committee_id):
    clear_scores_session_state()
    st.session_state["prev_exam_id"] = exam_id
    st.session_state["prev_committee_id"] = committee_id

# โหลดคะแนนถ้ามี record จริง
if record:
    load_scores_to_session(record)
else:
    # ถ้าไม่มี record ให้ตั้งเป็น 0 แต่ session_state อาจเคลียร์ไปแล้วข้างบน
    pass

# ---------- RADIO GROUP ----------
def radio_group(title, questions):
    st.markdown(f"### {title}")
    total = 0
    for q in questions:
        score = st.radio(
            q,
            options=[0, 1, 2, 3, 4, 5],
            horizontal=True,
            index=st.session_state.get(q, 0),
            key=q
        )
        total += score
    return total

st.divider()
st.subheader("กรุณาให้คะแนนแต่ละหัวข้อ (0 - 5)")

sum1 = radio_group("1. บุคลิกภาพและการพูด", all_questions[0:4])
sum2 = radio_group("2. ปฏิภาณไหวพริบ", all_questions[4:8])
sum3 = radio_group("3. ความรู้และความเข้าใจ", all_questions[8:12])
sum4 = radio_group("4. เป้าหมายและทัศนคติ", all_questions[12:16])
sum5 = radio_group("5. คุณธรรม/จริยธรรมทหาร", all_questions[16:20])

total_score = sum1 + sum2 + sum3 + sum4 + sum5
st.success(f"คะแนนรวมทั้งหมด: {total_score} คะแนน")

comment = st.text_area("ความคิดเห็นเพิ่มเติม", st.session_state.get("comment", ""))
st.session_state["comment"] = comment

# ---------- FIND ROW ----------
def find_existing_row(records, exam_id, committee_id):
    for i, row in enumerate(records, start=2):  # header is row 1
        if str(row.get("exam_id", "")) == exam_id and str(row.get("committee_id", "")) == committee_id:
            return i
    return None

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

# ---------- SUBMIT ----------
if st.button("บันทึกคะแนน"):
    new_row = [
        exam_id, committee_id, name,
        exam_date.strftime('%Y-%m-%d'), time,
        sum1, sum2, sum3, sum4, sum5,
        total_score, comment
    ]

    for q in all_questions:
        new_row.append(st.session_state[q])

    try:
        if existing_row and confirm_update == "ใช่":
            end_col = chr(ord('A') + len(new_row) - 1)
            sheet.update(f"A{existing_row}:{end_col}{existing_row}", [new_row])
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
    except Exception:
        st.error("❌ เกิดข้อผิดพลาดระหว่างบันทึกข้อมูล")
        st.code(traceback.format_exc())
