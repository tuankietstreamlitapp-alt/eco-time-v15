import math
import time
import datetime
import gspread
import pandas as pd
import pytz
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="4567 Xe Ôm — Tài Xế (v4.6 Test Native)", page_icon="🛵", layout="centered"
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

def delete_row_from_sheet(tab_name, col_name, target_val):
    try:
        ws, records = get_worksheet_data(tab_name)
        if ws is None or not records:
            return False
        for i, row in enumerate(records, start=2):
            if str(row.get(col_name, "")) == str(target_val):
                ws.delete_rows(i)
                return True
        return False
    except Exception as e:
        return False

# ============================================================
# HÀM TÍNH CƯỚC BẬC THANG CHUẨN
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
# CSS GIAO DIỆN CHUYÊN NGHIỆP
# ============================================================
st.markdown(
    """
    <style>
    .stApp { background-color: #f1f5f9; }
    .block-container { max-width: 550px; padding: 1.0rem 1rem 2rem 1rem; }
    
    .pro-card {
        background: #ffffff;
        border-radius: 20px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
        border: 1px solid #e2e8f0;
    }
    
    .driver-header { 
        background: linear-gradient(135deg, #059669 0%, #047857 100%); 
        padding: 16px 20px; 
        border-radius: 20px; 
        color: white; 
        margin-bottom: 14px; 
        box-shadow: 0 10px 20px rgba(5, 150, 105, 0.2); 
    }
    .driver-name { font-size: 19px; font-weight: 800; margin: 0; color: white; letter-spacing: -0.3px; }
    .driver-phone { font-size: 13px; margin-top: 3px; color: #d1fae5; font-weight: 600; }
    
    div.stButton > button { 
        border-radius: 16px !important; 
        font-weight: 800 !important; 
        font-size: 17px !important; 
        min-height: 54px !important; 
        background-color: #059669 !important; 
        color: white !important; 
        border: none !important; 
        box-shadow: 0 8px 20px rgba(5, 150, 105, 0.25);
        transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1) !important;
        cursor: pointer !important;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 24px rgba(5, 150, 105, 0.35) !important;
        filter: brightness(1.05);
    }
    div.stButton > button:active {
        transform: scale(0.97) translateY(0px) !important;
    }

    input { 
        font-size: 16px !important; 
        font-weight: 600 !important; 
        border-radius: 12px !important;
        border: 1.5px solid #cbd5e1 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# KHỞI TẠO SESSION STATE MẶC ĐỊNH
# ============================================================
if "step" not in st.session_state:
    st.session_state["step"] = 1  # 1: Đăng nhập, 2: Hành trình, 3: Hóa đơn

defaults = {
    "user_phone": "",
    "user_name": "",
    "cust_name": "",
    "cust_phone": "",
    "trip_id": "",
    "trip_started_at": None,
    "final_dist": 0.0,
    "final_end_ts": None,
    "trip_active_state": False,
    "saved_to_sheet": False
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ============================================================
# ĐIỀU HƯỚNG CẤU TRÚC RẼ NHÁNH IF-ELIF (100% NATIVE STREAMLIT)
# ============================================================

# --- BƯỚC 1: MÀN HÌNH ĐĂNG NHẬP ---
if st.session_state["step"] == 1:
    st.markdown(
        """
        <div class="pro-card" style="text-align: center; padding: 24px 20px; margin-top: 10px;">
            <div style="font-size: 42px; margin-bottom: 6px;">🛵</div>
            <div style="font-size: 22px; font-weight: 900; color: #0f172a; letter-spacing: -0.5px;">4567 XE ÔM (TEST NATIVE)</div>
            <div style="font-size: 13px; color: #64748b; font-weight: 600; margin-top: 2px;">Kiểm tra cô lập lỗi giao diện</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    phone_input = st.text_input("Số điện thoại tài xế:", placeholder="Nhập SĐT của bác...")
    
    st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
    if st.button("ĐĂNG NHẬP HỆ THỐNG", use_container_width=True):
        if phone_input.strip() == "":
            st.warning("⚠️ Bác ơi, vui lòng nhập số điện thoại của mình nhé!")
        else:
            with st.spinner("Đang xác thực thông tin..."):
                _, login_records = get_worksheet_data("DANG_NHAP")
                matched_user = None
                for row in login_records:
                    if str(row.get("SĐT", "")).strip() == phone_input.strip():
                        matched_user = row
                        break
                
                if matched_user:
                    st.session_state["user_phone"] = str(matched_user.get("SĐT", ""))
                    st.session_state["user_name"] = str(matched_user.get("TÊN TÀI XẾ", "Tài xế"))
                    st.session_state["step"] = 2
                    st.success(f"Chào bác **{st.session_state['user_name']}**! Đang vào ứng dụng...")
                    time.sleep(0.4)
                    st.rerun()
                else:
                    st.error("❌ Số điện thoại không đúng hoặc chưa được cấp quyền!")

# --- BƯỚC 2 & 3: KHU VỰC ĐÃ ĐĂNG NHẬP ---
else:
    # Header & Nút Đăng xuất
    col_info, col_logout = st.columns([3, 1])
    with col_info:
        st.markdown(
            f"""
            <div class="driver-header" style="margin-bottom: 0px;">
                <div class="driver-name">👨‍✈️ {st.session_state['user_name']}</div>
                <div class="driver-phone">📞 {st.session_state['user_phone']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_logout:
        st.markdown("<div style='margin-top: 4px;'></div>", unsafe_allow_html=True)
        if st.button("🚪 Đăng xuất", use_container_width=True, help="Thoát tài khoản"):
            st.session_state["step"] = 1
            st.session_state["user_phone"] = ""
            st.session_state["user_name"] = ""
            st.session_state["trip_active_state"] = False
            st.session_state["saved_to_sheet"] = False
            st.session_state["trip_started_at"] = None
            st.session_state["final_dist"] = 0.0
            st.session_state["final_end_ts"] = None
            st.rerun()

    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

    # --- BƯỚC 2: MÀN HÌNH NHẬP KHÁCH & ĐO HÀNH TRÌNH (NATIVE) ---
    if st.session_state["step"] == 2:
        if not st.session_state["trip_active_state"]:
            st.markdown(
                """
                <div class="pro-card">
                    <div style="font-size: 15px; font-weight: 800; color: #0f172a; margin-bottom: 10px;">📝 Bước 1: Khởi tạo cuốc xe</div>
                """,
                unsafe_allow_html=True,
            )
            cust_name_in = st.text_input("Tên khách hàng (Tùy chọn):", placeholder="VD: Anh Nam")
            cust_phone_in = st.text_input("SĐT khách hàng (Tùy chọn):", placeholder="VD: 0912345678")
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
            if st.button("🟢 BẮT ĐẦU HÀNH TRÌNH", use_container_width=True):
                st.session_state["trip_active_state"] = True
                st.session_state["trip_started_at"] = time.time()
                st.session_state["cust_name"] = cust_name_in.strip() if cust_name_in.strip() else "Khách vãng lai"
                st.session_state["cust_phone"] = cust_phone_in.strip()
                st.session_state["trip_id"] = f"C4567_{int(st.session_state['trip_started_at'])}"
                
                start_time_str = get_vn_time(st.session_state["trip_started_at"])
                stt_cache = get_next_stt("CACHE_4567")
                cache_row = [
                    stt_cache, st.session_state["trip_id"], start_time_str, "---", "---",
                    st.session_state["cust_name"], st.session_state["cust_phone"], 0,
                    st.session_state['user_name'], "---", 0, 0, "BẮT ĐẦU CUỐC"
                ]
                append_row_to_sheet("CACHE_4567", cache_row)
                st.rerun()
        
        else:
            st.markdown(
                f"""
                <div class="pro-card" style="border-left: 5px solid #059669; background: #f8fafc;">
                    <div style="color: #059669; font-size: 12px; font-weight: 800; text-transform: uppercase;">🟢 ĐANG TRONG CHUYẾN ĐI (CHẾ ĐỘ NATIVE)</div>
                    <div style="font-size: 14px; color: #1e293b; margin-top: 4px; font-weight: 700;">Khách: {st.session_state.get('cust_name', 'Khách vãng lai')} &bull; SĐT: {st.session_state.get('cust_phone', '---')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Tính thời gian trôi qua trực tiếp bằng Python
            elapsed_seconds = int(time.time() - st.session_state["trip_started_at"])
            hh = elapsed_seconds // 3600
            mm = (elapsed_seconds % 3600) // 60
            ss = elapsed_seconds % 60

            st.markdown(
                f"""
                <div style="background: linear-gradient(135deg, #064e3b 0%, #022c22 100%); border-radius: 20px; padding: 20px 16px; margin-bottom: 12px; text-align: center; box-shadow: 0 10px 25px rgba(2, 44, 34, 0.2);">
                    <div style="color: #34d399; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px;">ĐỒNG HỒ NATIVE STREAMLIT</div>
                    <div style="color: #ffffff; font-size: 40px; font-weight: 900; margin: 4px 0; letter-spacing: -1px;">{hh:02d}:{mm:02d}:{ss:02d}</div>
                    <div style="color: #a7f3d0; font-size: 12px; margin-top: 8px; font-weight: 600;">Đã gỡ bỏ iframe GPS để kiểm tra lỗi nhân bản màn hình</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_ref, col_pay = st.columns(2)
            with col_ref:
                if st.button("🔄 Cập nhật giờ", use_container_width=True):
                    st.rerun()
            with col_pay:
                if st.button("💵 THANH TOÁN", use_container_width=True):
                    st.session_state["final_end_ts"] = time.time()
                    # Giả lập quãng đường 4.5km cho bản test này để kiểm tra hệ thống hóa đơn
                    st.session_state["final_dist"] = 4500.0
                    st.session_state["step"] = 3
                    st.rerun()

    # --- BƯỚC 3: MÀN HÌNH HÓA ĐƠN CHI TIẾT ---
    elif st.session_state["step"] == 3:
        start_ts = st.session_state["trip_started_at"]
        end_ts = st.session_state["final_end_ts"]
        dist_val = st.session_state["final_dist"]
        cname = st.session_state["cust_name"]
        cphone = st.session_state["cust_phone"]
        trip_id = st.session_state["trip_id"]

        start_time_str = get_vn_time(start_ts)
        end_time_str = get_vn_time(end_ts)
        
        time_diff = max(0, int(end_ts - start_ts))
        hh, mm, ss = time_diff // 3600, (time_diff % 3600) // 60, time_diff % 60
        total_time_str = f"{hh:02d}:{mm:02d}:{ss:02d}"

        km_val = round(dist_val / 1000.0, 2)
        fare_val = calculate_fare(km_val)
        driver_name_val = st.session_state.get('user_name', 'Tài xế')
        unit_desc = get_current_unit_price_desc(km_val)
        
        # Lưu Google Sheets 1 lần duy nhất
        if not st.session_state["saved_to_sheet"]:
            stt = get_next_stt("DATA_4567")
            row_data = [
                stt, trip_id, start_time_str, end_time_str, total_time_str,
                cname, cphone, fare_val, driver_name_val,
                unit_desc, km_val, fare_val, "ĐÃ THANH TOÁN"
            ]
            append_row_to_sheet("DATA_4567", row_data)
            delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)
            st.session_state["saved_to_sheet"] = True

        if st.button("⬅️ QUAY LẠI MÀN HÌNH CHÍNH", use_container_width=True):
            st.session_state["trip_active_state"] = False
            st.session_state["saved_to_sheet"] = False
            st.session_state["step"] = 2
            st.rerun()

        # Hiển thị hóa đơn hoàn toàn bằng Native Markdown/HTML tĩnh không qua iframe
        st.markdown(
            f"""
            <div style="background: #ffffff; border-radius: 20px; padding: 18px 20px; border: 2px solid #059669; box-shadow: 0 10px 25px rgba(0,0,0,0.05); margin-top: 10px;">
                <div style="text-align: center; border-bottom: 2px dashed #cbd5e1; padding-bottom: 12px; margin-bottom: 12px;">
                    <div style="font-size: 32px;">🧾</div>
                    <div style="font-size: 19px; font-weight: 900; color: #064e3b; margin-top: 4px;">HÓA ĐƠN CHI TIẾT CHUYẾN ĐI</div>
                    <div style="font-size: 12px; color: #64748b; font-weight: 700; margin-top: 2px;">Mã cuốc: {trip_id}</div>
                </div>
                
                <div style="font-size: 14px; color: #334155; line-height: 1.7;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span style="color: #64748b; font-weight: 600;">Khách hàng:</span>
                        <span style="font-weight: 800; color: #0f172a; text-align: right;">{cname} ({cphone if cphone else 'Không có SĐT'})</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span style="color: #64748b; font-weight: 600;">Tài xế:</span>
                        <span style="font-weight: 800; color: #0f172a;">{driver_name_val}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span style="color: #64748b; font-weight: 600;">Giờ khởi hành:</span>
                        <span style="font-weight: 700; color: #0f172a;">{start_time_str}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span style="color: #64748b; font-weight: 600;">Giờ kết thúc:</span>
                        <span style="font-weight: 700; color: #0f172a;">{end_time_str}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span style="color: #64748b; font-weight: 600;">Thời gian đi:</span>
                        <span style="font-weight: 700; color: #0f172a;">{total_time_str}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span style="color: #64748b; font-weight: 600;">Quãng đường:</span>
                        <span style="font-weight: 800; color: #059669;">{km_val} km</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #64748b; font-weight: 600;">Mức giá:</span>
                        <span style="font-weight: 700; color: #d97706; font-size: 13px; text-align: right;">{unit_desc}</span>
                    </div>
                </div>
                
                <div style="margin-top: 14px; padding-top: 12px; border-top: 2px dashed #cbd5e1; text-align: center;">
                    <div style="font-size: 12px; color: #64748b; font-weight: 700; text-transform: uppercase;">Tổng thành tiền</div>
                    <div style="font-size: 36px; font-weight: 900; color: #059669; margin-top: 2px;">{format(fare_val, ',')} VNĐ</div>
                    <div style="font-size: 11px; color: #10b981; font-weight: 700; margin-top: 2px;">✅ Đã thanh toán & đồng bộ lên Google Sheets</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
