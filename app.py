import math
import time
import datetime
import gspread
import pandas as pd
import pytz
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="4567 Xe Ôm — Tài Xế (v3.0)", page_icon="🛵", layout="centered"
)

# ============================================================
# CẤU HÌNH MÚI GIỜ VIỆT NAM (UTC+7)
# ============================================================
def get_vn_time(timestamp=None):
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    if timestamp is None:
        return datetime.datetime.now(vn_tz).strftime('%Y-%m-%d %H:%M:%S')
    return datetime.datetime.fromtimestamp(timestamp, vn_tz).strftime('%Y-%m-%d %H:%M:%S')

# ============================================================
# CẤU HÌNH KẾT NỐI GOOGLE SHEETS
# ============================================================
SHEET_KEY = st.secrets["connections"]["gsheets"].get("spreadsheet", "1A3-1am25vZLN57SD7pkfxxQtymCaPnCj9HgBpw5RcTY")

@st.cache_resource
def init_google_sheet_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["connections"]["gsheets"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client

def get_worksheet_data(tab_name):
    try:
        client = init_google_sheet_client()
        sheet = client.open_by_key(SHEET_KEY)
        ws = sheet.worksheet(tab_name)
        return ws, ws.get_all_records()
    except Exception as e:
        return None, []

def get_next_stt(tab_name):
    try:
        _, records = get_worksheet_data(tab_name)
        if not records:
            return 1
        return len(records) + 1
    except Exception:
        return 1

def append_row_to_sheet(tab_name, row_values):
    try:
        client = init_google_sheet_client()
        sheet = client.open_by_key(SHEET_KEY)
        ws = sheet.worksheet(tab_name)
        ws.append_row(row_values)
        return True
    except Exception as e:
        return False

# ============================================================
# HÀM TÍNH CƯỚC THEO BIỂU GIÁ BẬC THANG CHUẨN (v3.0)
# ============================================================
def calculate_fare(km):
    if km < 3.0:
        return 0
    elif km < 11.0:
        return round(km * 4500)
    elif km < 40.0:
        return round(km * 4000)
    else:
        return round(km * 5500)

def get_current_unit_price_desc(km):
    if km < 3.0:
        return "0 đ/km (Miễn phí < 3km)"
    elif km < 11.0:
        return "4,500 đ/km (3km - dưới 11km)"
    elif km < 40.0:
        return "4,000 đ/km (11km - dưới 40km)"
    else:
        return "5,500 đ/km (Từ 40km trở lên)"

# ============================================================
# CSS GIAO DIỆN TỐI ƯU TRẢI NGHIỆM (UI/UX CHUYÊN NGHIỆP)
# ============================================================
st.markdown(
    """
    <style>
    .stApp { background-color: #f8fafc; }
    .block-container { max-width: 600px; padding-top: 1.5rem; padding-bottom: 2rem; padding-left: 1rem; padding-right: 1rem; }
    .driver-header { background: linear-gradient(135deg, #00A86B 0%, #007A4D 100%); padding: 16px 20px; border-radius: 16px; color: white; margin-bottom: 14px; box-shadow: 0 4px 12px rgba(0, 168, 107, 0.2); }
    .driver-name { font-size: 19px; font-weight: 900; margin: 0; color: white; }
    .driver-phone { font-size: 13px; margin-top: 3px; color: #e2e8f0; font-weight: 600; }
    
    div.stButton > button { 
        border-radius: 14px !important; 
        font-weight: 900 !important; 
        font-size: 17px !important; 
        min-height: 54px !important; 
        background-color: #00A86B !important; 
        color: white !important; 
        border: none !important; 
        box-shadow: 0 4px 12px rgba(0, 168, 107, 0.25);
        transition: transform 0.1s ease, background-color 0.1s ease !important;
    }
    div.stButton > button:active { 
        transform: scale(0.97) !important; 
    }
    div.stButton > button:hover { 
        background-color: #008f5a !important; 
    }
    input { font-size: 16px !important; font-weight: 600 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# KHỞI TẠO SESSION STATE AN TOÀN
# ============================================================
defaults = {
    "logged_in": False,
    "user_phone": "",
    "user_name": "",
    "cust_name": "",
    "cust_phone": "",
    "trip_active": False,
    "trip_id": "",
    "trip_started_at": None
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ============================================================
# MÀN HÌNH 1: ĐĂNG NHẬP TÀI XẾ
# ============================================================
if not st.session_state["logged_in"]:
    st.markdown(
        """
        <div style="text-align: center; padding: 20px 0 10px 0;">
            <div style="font-size: 38px;">🛵</div>
            <div style="font-size: 22px; font-weight: 900; color: #0f172a; margin-top: 4px;">4567 XE ÔM (v3.0 NATIVE)</div>
            <div style="font-size: 13px; color: #64748b;">Hệ thống quản lý chuyên nghiệp & ổn định tuyệt đối</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("### 🔐 Đăng nhập tài khoản")
    phone_input = st.text_input("Số điện thoại tài xế:", placeholder="Ví dụ: 0978666620")
    
    if st.button("ĐĂNG NHẬP HỆ THỐNG", use_container_width=True):
        if phone_input.strip() == "":
            st.warning("⚠️ Bác ơi, vui lòng nhập số điện thoại của mình nhé!")
        else:
            with st.spinner("Đang xác thực tài khoản..."):
                _, login_records = get_worksheet_data("DANG_NHAP")
                matched_user = None
                for row in login_records:
                    if str(row.get("SĐT", "")).strip() == phone_input.strip():
                        matched_user = row
                        break
                
                if matched_user:
                    st.session_state["logged_in"] = True
                    st.session_state["user_phone"] = str(matched_user.get("SĐT", ""))
                    st.session_state["user_name"] = str(matched_user.get("TÊN TÀI XẾ", "Tài xế"))
                    st.success(f"Chào bác **{st.session_state['user_name']}**! Đang chuyển vào giao diện chính...")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Số điện thoại không đúng hoặc chưa được cấp quyền!")
    st.stop()

# ============================================================
# HEADER THÔNG TIN TÀI XẾ
# ============================================================
st.markdown(
    f"""
    <div class="driver-header">
        <div class="driver-name">👨‍✈️ Tài xế: {st.session_state['user_name']}</div>
        <div class="driver-phone">📞 SĐT: {st.session_state['user_phone']}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# MÀN HÌNH 2: NHẬP THÔNG TIN KHÁCH HÀNG
# ============================================================
if not st.session_state["trip_active"]:
    st.markdown("### 📝 Bước 1: Thông tin khách hàng")
    cust_name_in = st.text_input("Tên khách hàng (Không bắt buộc):", placeholder="VD: Anh Nam")
    cust_phone_in = st.text_input("SĐT khách hàng (Không bắt buộc):", placeholder="VD: 0912345678")
    
    st.write("")
    if st.button("🟢 BẮT ĐẦU HÀNH TRÌNH", use_container_width=True):
        st.session_state["trip_active"] = True
        st.session_state["trip_started_at"] = time.time()
        st.session_state["cust_name"] = cust_name_in.strip() if cust_name_in.strip() else "Khách vãng lai"
        st.session_state["cust_phone"] = cust_phone_in.strip()
        st.session_state["trip_id"] = f"C4567_{int(st.session_state['trip_started_at'])}"
        st.rerun()

# ============================================================
# MÀN HÌNH 3: THEO DÕI HÀNH TRÌNH & KẾT THÚC (100% PYTHON NATIVE)
# ============================================================
else:
    st.markdown(
        f"""
        <div style="background: #ffffff; border: 2px solid #00A86B; border-radius: 16px; padding: 14px 16px; margin-bottom: 12px;">
            <div style="color: #00A86B; font-size: 13px; font-weight: 800; text-transform: uppercase;">🟢 BƯỚC 2: HÀNH TRÌNH ĐANG DIỄN RA</div>
            <div style="font-size: 14px; color: #334155; margin-top: 4px;">Khách: <b>{st.session_state.get('cust_name', 'Khách vãng lai')}</b> | SĐT: <b>{st.session_state.get('cust_phone', '---')}</b></div>
            <div style="font-size: 12px; color: #64748b; margin-top: 2px;">Thời điểm xuất phát: <b>{get_vn_time(st.session_state['trip_started_at'])}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Tính thời gian đã trôi qua
    elapsed_sec = int(time.time() - st.session_state['trip_started_at'])
    hh, mm, ss = elapsed_sec // 3600, (elapsed_sec % 3600) // 60, elapsed_sec % 60
    time_str = f"{hh:02d}:{mm:02d}:{ss:02d}"

    st.markdown(
        f"""
        <div style="background: #f0fdf4; border: 2px solid #86efac; border-radius: 14px; padding: 16px; text-align: center; margin-bottom: 14px;">
            <div style="color: #166534; font-size: 12px; font-weight: 800; text-transform: uppercase;">⏱ THỜI GIAN CHUYẾN ĐI</div>
            <div style="color: #0f172a; font-size: 38px; font-weight: 900; margin: 4px 0;">{time_str}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 🛣 Nhập quãng đường thực tế (km)")
    km_input = st.number_input(
        "Số kilomet chạy được (đọc từ đồng hồ xe hoặc định mức):",
        min_value=0.0,
        max_value=500.0,
        value=0.0,
        step=0.1,
        format="%.1f"
    )

    # Tính cước tạm tính ngay lập tức để minh bạch với khách
    current_fare = calculate_fare(km_input)
    current_desc = get_current_unit_price_desc(km_input)

    st.markdown(
        f"""
        <div style="background: #ffffff; border: 1px solid #cbd5e1; border-radius: 14px; padding: 14px; margin-bottom: 16px; text-align: center;">
            <div style="font-size: 12px; color: #64748b; font-weight: 700;">CƯỚC PHÍ TẠM TÍNH</div>
            <div style="font-size: 32px; font-weight: 900; color: #00A86B; margin: 2px 0;">{current_fare:,.0f} VNĐ</div>
            <div style="font-size: 12px; color: #475569; font-weight: 600;">Đơn giá: {current_desc}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 LÀM MỚI GIỜ", use_container_width=True):
            st.rerun()
    with col2:
        pass

    st.write("")
    if st.button("🔴 XÁC NHẬN KẾT THÚC & LƯU CUỐC XE", use_container_width=True):
        if km_input <= 0.0:
            st.warning("⚠️ Bác ơi, vui lòng nhập số km thực tế trước khi kết thúc chuyến nhé!")
        else:
            with st.spinner("Đang lưu dữ liệu lên hệ thống..."):
                end_ts = time.time()
                start_ts = st.session_state['trip_started_at']
                
                start_time_str = get_vn_time(start_ts)
                end_time_str = get_vn_time(end_ts)
                
                time_diff = max(0, int(end_ts - start_ts))
                th, tm, ts = time_diff // 3600, (time_diff % 3600) // 60, time_diff % 60
                total_time_str = f"{th:02d}:{tm:02d}:{ts:02d}"

                km_val = round(km_input, 2)
                fare_val = calculate_fare(km_val)
                trip_id = st.session_state['trip_id']
                cname = st.session_state['cust_name']
                cphone = st.session_state['cust_phone']
                driver_name = st.session_state['user_name']

                stt = get_next_stt("DATA_4567")
                row_data = [
                    stt, trip_id, start_time_str, end_time_str, total_time_str,
                    cname, cphone, fare_val, driver_name,
                    get_current_unit_price_desc(km_val), km_val, fare_val, "HOÀN THÀNH CUỐC XE"
                ]
                
                success = append_row_to_sheet("DATA_4567", row_data)
                
                if success:
                    st.success("✅ Đã lưu cuốc xe thành công lên Google Sheets!")
                    time.sleep(0.8)
                    st.session_state["trip_active"] = False
                    st.session_state["cust_name"] = ""
                    st.session_state["cust_phone"] = ""
                    st.session_state["trip_id"] = ""
                    st.session_state["trip_started_at"] = None
                    st.rerun()
                else:
                    st.error("❌ Lỗi kết nối Google Sheets! Vui lòng bấm lưu lại.")
