import math
import time
import datetime
import json
import html
import gspread
import pandas as pd
import pytz
import streamlit as st
import streamlit.components.v1 as components
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="4567 Xe Ôm — Tài Xế (v4.4 Pro)", page_icon="🛵", layout="centered"
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

def trip_exists_in_sheet(tab_name, trip_id):
    """Kiểm tra mã cuốc đã tồn tại để tránh ghi trùng khi mạng trả lỗi/timeout."""
    try:
        _, records = get_worksheet_data(tab_name)
        target = str(trip_id).strip()
        return any(str(row.get("MÃ CUỐC XE", "")).strip() == target for row in records)
    except Exception:
        return False


def get_active_cache_for_driver(driver_name):
    """Lấy cuốc chưa hoàn tất gần nhất để khôi phục sau refresh/mất phiên."""
    try:
        _, records = get_worksheet_data("CACHE_4567")
        if not records:
            return None

        candidates = []
        for row in records:
            status = str(row.get("TRẠNG THÁI", "")).strip().upper()
            row_driver = str(row.get("TÊN TÀI XẾ", "")).strip()
            end_time = str(row.get("GIỜ KẾT THÚC", "")).strip()
            if (row_driver == str(driver_name).strip()
                    and status in {"BẮT ĐẦU CUỐC", "ĐANG CHẠY XE"}
                    and end_time in {"", "---"}):
                trip_id = str(row.get("MÃ CUỐC XE", "")).strip()
                if trip_id:
                    candidates.append(row)

        if not candidates:
            return None

        # Chỉ đọc DATA_4567 một lần để tránh nhiều request Google Sheets.
        _, data_records = get_worksheet_data("DATA_4567")
        completed_ids = {
            str(row.get("MÃ CUỐC XE", "")).strip()
            for row in data_records
            if str(row.get("MÃ CUỐC XE", "")).strip()
        }
        for row in reversed(candidates):
            if str(row.get("MÃ CUỐC XE", "")).strip() not in completed_ids:
                return row
        return None
    except Exception:
        return None

def get_trip_start_timestamp(trip_id, fallback=None):
    try:
        return float(str(trip_id).rsplit("_", 1)[-1])
    except (ValueError, TypeError):
        return fallback if fallback is not None else time.time()


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


def set_payment_method_in_sheet(tab_name, trip_id, payment_method):
    """Ghi phương thức thanh toán vào cột PHƯƠNG THỨC THANH TOÁN; tự tạo cột nếu chưa có."""
    try:
        ws, records = get_worksheet_data(tab_name)
        if ws is None:
            return False
        header = ws.row_values(1)
        col_idx = None
        for idx, h in enumerate(header, start=1):
            if str(h).strip().upper() == "PHƯƠNG THỨC THANH TOÁN":
                col_idx = idx
                break
        if col_idx is None:
            col_idx = len(header) + 1
            ws.update_cell(1, col_idx, "PHƯƠNG THỨC THANH TOÁN")
        for i, row in enumerate(records, start=2):
            if str(row.get("MÃ CUỐC XE", "")).strip() == str(trip_id).strip():
                ws.update_cell(i, col_idx, payment_method)
                return True
        return False
    except Exception:
        return False

# ============================================================
# CẬP NHẬT HIỆN TRẠNG TÀI XẾ TRÊN SHEET DANG_NHAP
# ============================================================
def update_driver_status(phone, status_text):
    try:
        ws, records = get_worksheet_data("DANG_NHAP")
        if ws is None or not records:
            return False
        
        header = ws.row_values(1)
        col_idx = None
        for idx, h in enumerate(header, start=1):
            if str(h).strip().upper() == "HIỆN TRẠNG TÀI XẾ":
                col_idx = idx
                break
        
        if col_idx is None:
            col_idx = len(header) + 1
            ws.update_cell(1, col_idx, "HIỆN TRẠNG TÀI XẾ")

        for i, row in enumerate(records, start=2):
            if str(row.get("SĐT", "")).strip() == str(phone).strip():
                ws.update_cell(i, col_idx, status_text)
                return True
        return False
    except Exception:
        return False

# ============================================================
# ĐỌC BẢNG GIÁ ĐỘNG TỪ SHEET BANG_GIA
# ============================================================
def get_pricing_tiers():
    ws, records = get_worksheet_data("BANG_GIA")
    tiers = []
    if records:
        for r in records:
            try:
                from_km = float(r.get("TỪ KM", 0))
                to_km = float(r.get("ĐẾN KM", 999999))
                price = float(r.get("ĐƠN GIÁ", 0))
                desc = str(r.get("MÔ TẢ", f"{price:,.0f} đ/km"))
                tiers.append({
                    "from": from_km,
                    "to": to_km,
                    "price": price,
                    "desc": desc
                })
            except Exception:
                continue
    
    if not tiers:
        tiers = [
            {"from": 0.0, "to": 3.0, "price": 0, "desc": "0 đ/km (Miễn phí < 3km)"},
            {"from": 3.0, "to": 11.0, "price": 4500, "desc": "4,500 đ/km (3km - dưới 11km)"},
            {"from": 11.0, "to": 40.0, "price": 4000, "desc": "4,000 đ/km (11km - dưới 40km)"},
            {"from": 40.0, "to": 999999.0, "price": 5500, "desc": "5,500 đ/km (Từ 40km trở lên)"}
        ]
    return tiers

def calculate_fare(km):
    tiers = get_pricing_tiers()
    for t in tiers:
        if t["from"] <= km < t["to"]:
            return round(km * t["price"])
    if tiers:
        return round(km * tiers[-1]["price"])
    return 0

def get_current_unit_price_desc(km):
    tiers = get_pricing_tiers()
    for t in tiers:
        if t["from"] <= km < t["to"]:
            return t["desc"]
    if tiers:
        return tiers[-1]["desc"]
    return "Đơn giá chưa xác định"

def safe_html(value):
    return html.escape(str(value or ""), quote=True)


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
    .driver-name { font-size: 20px; font-weight: 800; margin: 0; color: white; letter-spacing: -0.3px; }
    .driver-phone { font-size: 14px; margin-top: 4px; color: #d1fae5; font-weight: 600; }
    
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

    .action-btn { font-family: inherit; }
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
# QUẢN LÝ TRẠNG THÁI 3 CỬA SỔ RIÊNG BIỆT
# ============================================================
if "step" not in st.session_state:
    st.session_state["step"] = 1  # 1: Đăng nhập, 2: Nhận khách & Đo GPS, 3: Hóa đơn chi tiết

defaults = {
    "user_phone": "",
    "user_name": "",
    "cust_name": "",
    "cust_phone": "",
    "trip_id": "",
    "trip_started_at": None,
    "final_dist": 0.0,
    "final_end_ts": None,
    "final_elapsed": 0,
    "trip_active_state": False,
    "saved_to_sheet": False,
    "payment_pending": False,
    "payment_method": "",
    "payment_confirmed": False
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

GPS_ACCURACY_MAX_M = 50
MIN_MOVE_M = 3

# Bắt tín hiệu kết thúc chuyến từ JS đẩy qua query params
if "action" in st.query_params and st.query_params["action"] in {"stop", "checkout"}:
    try:
        st.session_state["final_dist"] = max(0.0, float(st.query_params.get("dist", 0.0)))
    except (TypeError, ValueError):
        st.session_state["final_dist"] = 0.0

    try:
        start_ts = float(st.query_params.get("start", time.time()))
    except (TypeError, ValueError):
        start_ts = time.time()

    try:
        elapsed_seconds = max(0, int(float(st.query_params.get("elapsed", 0))))
    except (TypeError, ValueError):
        elapsed_seconds = 0

    st.session_state["trip_started_at"] = start_ts
    st.session_state["final_end_ts"] = time.time()
    st.session_state["final_elapsed"] = elapsed_seconds
    st.session_state["cust_name"] = st.query_params.get("cname", "Khách vãng lai")
    st.session_state["cust_phone"] = st.query_params.get("cphone", "")
    st.session_state["trip_id"] = f"C4567_{int(start_ts)}"
    st.session_state["payment_pending"] = True
    st.session_state["payment_confirmed"] = False
    st.session_state["payment_method"] = ""
    st.session_state["saved_to_sheet"] = False
    st.query_params.clear()
    st.session_state["step"] = 3
    st.rerun()

# ============================================================
# CỬA SỔ 1: MÀN HÌNH ĐĂNG NHẬP
# ============================================================
if st.session_state["step"] == 1:
    st.markdown(
        """
        <div class="pro-card" style="text-align: center; padding: 24px 20px; margin-top: 10px;">
            <div style="font-size: 42px; margin-bottom: 6px;">🛵</div>
            <div style="font-size: 22px; font-weight: 900; color: #0f172a; letter-spacing: -0.5px;">4567 XE ÔM PRO</div>
            <div style="font-size: 13px; color: #64748b; font-weight: 600; margin-top: 2px;">Hệ thống định vị & điều hành chuyên nghiệp</div>
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

                    # Khôi phục cuốc đang chạy nếu phiên Streamlit/browser vừa bị mất.
                    active_cache = get_active_cache_for_driver(st.session_state["user_name"])
                    if active_cache:
                        restored_trip_id = str(active_cache.get("MÃ CUỐC XE", "")).strip()
                        restored_start = get_trip_start_timestamp(restored_trip_id)
                        st.session_state["trip_id"] = restored_trip_id
                        st.session_state["trip_started_at"] = restored_start
                        st.session_state["cust_name"] = str(active_cache.get("TÊN KHÁCH HÀNG", "")).strip() or "Khách vãng lai"
                        st.session_state["cust_phone"] = str(active_cache.get("SĐT KHÁCH HÀNG", "")).strip()
                        st.session_state["trip_active_state"] = True
                        st.session_state["saved_to_sheet"] = False
                        st.session_state["step"] = 2
                        update_driver_status(st.session_state["user_phone"], "Đang chạy xe")
                        st.info("🔄 Đã khôi phục cuốc đang chạy từ CACHE_4567.")
                    else:
                        st.session_state["step"] = 2
                        update_driver_status(st.session_state["user_phone"], "Trực tuyến")
                        st.success(f"Chào bác **{st.session_state['user_name']}**! Đang vào ứng dụng...")
                    time.sleep(0.4)
                    st.rerun()
                else:
                    st.error("❌ Số điện thoại không đúng hoặc chưa được cấp quyền!")
    st.stop()

# ============================================================
# HEADER CHUNG CHO CỬA SỔ 2 & 3
# ============================================================
header_driver_name = safe_html(st.session_state.get("user_name", "Tài xế"))
header_driver_phone = safe_html(st.session_state.get("user_phone", ""))
st.markdown(
    f"""
    <div class="driver-header">
        <div class="driver-name">👨‍✈️ Tài xế: {header_driver_name}</div>
        <div class="driver-phone">📞 SĐT: {header_driver_phone}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# CỬA SỔ 2: NHẬP KHÁCH & ĐO GPS HÀNH TRÌNH
# ============================================================
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
            started_at = time.time()
            st.session_state["trip_active_state"] = True
            st.session_state["trip_started_at"] = started_at
            st.session_state["final_elapsed"] = 0
            st.session_state["cust_name"] = cust_name_in.strip() if cust_name_in.strip() else "Khách vãng lai"
            st.session_state["cust_phone"] = cust_phone_in.strip()
            st.session_state["trip_id"] = f"C4567_{int(started_at)}"
            st.session_state["saved_to_sheet"] = False
            st.session_state["payment_pending"] = False
            st.session_state["payment_method"] = ""
            st.session_state["payment_confirmed"] = False

            start_time_str = get_vn_time(started_at)
            stt_cache = get_next_stt("CACHE_4567")
            cache_row = [
                stt_cache, st.session_state["trip_id"], start_time_str, "---", "---",
                st.session_state["cust_name"], st.session_state["cust_phone"], 0,
                st.session_state["user_name"], "---", 0, 0, "BẮT ĐẦU CUỐC"
            ]
            cache_ok = append_row_to_sheet("CACHE_4567", cache_row)
            if not cache_ok:
                st.session_state["trip_active_state"] = False
                st.error("❌ Không thể ghi CACHE_4567. Vui lòng kiểm tra kết nối Google Sheets rồi thử lại.")
            else:
                update_driver_status(st.session_state["user_phone"], "Đang chạy xe")
                st.rerun()

    else:
        current_start_ts = st.session_state.get('trip_started_at', time.time())
        cname_val = st.session_state.get('cust_name', 'Khách vãng lai')
        cphone_val = st.session_state.get('cust_phone', '')
        cname_html = safe_html(cname_val)
        cphone_html = safe_html(cphone_val)
        tiers_json = json.dumps(get_pricing_tiers(), ensure_ascii=False)

        st.markdown(
            f"""
            <div class="pro-card" style="border-left: 5px solid #059669; background: #f8fafc;">
                <div style="color: #059669; font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;">🟢 ĐANG ĐO HÀNH TRÌNH GPS</div>
                <div style="font-size: 14px; color: #1e293b; margin-top: 4px; font-weight: 700;">Khách: {cname_html} &bull; SĐT: {cphone_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        current_start_ts = st.session_state.get('trip_started_at', time.time())
        cname_val = st.session_state.get('cust_name', 'Khách vãng lai')
        cphone_val = st.session_state.get('cust_phone', '')
        cname_html = safe_html(cname_val)
        cphone_html = safe_html(cphone_val)
        tiers_json = json.dumps(get_pricing_tiers(), ensure_ascii=False)
        
        html_live_tracker = f"""
        <div style="font-family: system-ui, -apple-system, sans-serif; padding: 2px;">
            <style>
                .action-btn {{
                    border: none;
                    border-radius: 16px;
                    padding: 14px;
                    font-size: 15px;
                    font-weight: 800;
                    cursor: pointer;
                    transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
                }}
                .action-btn:hover {{
                    filter: brightness(1.1);
                    transform: translateY(-2px);
                }}
                .action-btn:active {{
                    transform: scale(0.96) translateY(0px) !important;
                }}
            </style>

            <div id="toast_msg" style="visibility: hidden; background-color: #0f172a; color: #fff; text-align: center; border-radius: 12px; padding: 10px 16px; position: absolute; z-index: 100; left: 50%; transform: translateX(-50%); bottom: 85px; font-size: 13px; font-weight: 700; box-shadow: 0 10px 25px rgba(0,0,0,0.2); transition: opacity 0.3s ease; opacity: 0;">
                Thông báo
            </div>

            <div style="background: linear-gradient(135deg, #064e3b 0%, #022c22 100%); border-radius: 20px; padding: 20px 16px; margin-bottom: 12px; text-align: center; box-shadow: 0 10px 25px rgba(2, 44, 34, 0.2);">
                <div style="color: #34d399; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px;" id="status_label">ĐỒNG HỒ TÍNH CƯỚC THỜI GIAN THỰC</div>
                <div id="price" style="color: #ffffff; font-size: 40px; font-weight: 900; margin: 4px 0; letter-spacing: -1px;">0 VNĐ</div>
                <div style="display: flex; justify-content: space-around; margin-top: 12px; font-size: 14px; font-weight: 700; color: #e2e8f0; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 10px;">
                    <div>⏱ <span id="timer">00:00:00</span></div>
                    <div>🛣 <span id="km">0.00</span> km</div>
                </div>
                <div id="rate_desc" style="color: #a7f3d0; font-size: 12px; margin-top: 8px; font-weight: 600;">Đơn giá: Đang tải...</div>
            </div>
            
            <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                <button id="btnPause" class="action-btn" onclick="togglePause()" style="flex: 1; background: #d97706; color: white; box-shadow: 0 6px 16px rgba(217, 119, 6, 0.3);">
                    ⏸ TẠM DỪNG
                </button>
                <a id="btnPay" class="action-btn" href="#" target="_top" style="flex: 1.2; background: #059669; color: white; font-size: 15px; box-shadow: 0 6px 16px rgba(5, 150, 105, 0.3); text-decoration: none; display: flex; align-items: center; justify-content: center; box-sizing: border-box;">
                    💵 THANH TOÁN
                </a>
            </div>
            <div id="debug_acc" style="text-align: center; font-size: 11px; color: #64748b; font-weight: 600;">GPS: Đang bắt tín hiệu vệ tinh...</div>
        </div>

        <script>
        let isPaused = false;
        const tripStorageKey = "xeom_v5_" + {json.dumps(st.session_state['trip_id'], ensure_ascii=False)};
        let secondsElapsed = parseInt(localStorage.getItem(tripStorageKey + "_seconds") || "0", 10);
        let totalMeters = parseFloat(localStorage.getItem(tripStorageKey + "_meters") || "0.0");
        if (!Number.isFinite(secondsElapsed) || secondsElapsed < 0) secondsElapsed = 0;
        if (!Number.isFinite(totalMeters) || totalMeters < 0) totalMeters = 0;
        let startTimestamp = {current_start_ts};
        let customerName = {json.dumps(cname_val, ensure_ascii=False)};
        let customerPhone = {json.dumps(cphone_val, ensure_ascii=False)};
        let pricingTiers = {tiers_json};

        function vibrate(duration = 50) {{
            if (navigator.vibrate) {{ navigator.vibrate(duration); }}
        }}

        function showToast(text, bg = "#0f172a") {{
            let t = document.getElementById("toast_msg");
            t.innerText = text;
            t.style.backgroundColor = bg;
            t.style.visibility = "visible";
            t.style.opacity = "1";
            setTimeout(() => {{
                t.style.opacity = "0";
                t.style.visibility = "hidden";
            }}, 3000);
        }}

        function calculateFareJS(km) {{
            for (let i = 0; i < pricingTiers.length; i++) {{
                let t = pricingTiers[i];
                if (km >= t.from && km < t.to) {{
                    return Math.round(km * t.price);
                }}
            }}
            if (pricingTiers.length > 0) {{
                return Math.round(km * pricingTiers[pricingTiers.length - 1].price);
            }}
            return 0;
        }}

        function getRateDescJS(km) {{
            for (let i = 0; i < pricingTiers.length; i++) {{
                let t = pricingTiers[i];
                if (km >= t.from && km < t.to) {{
                    return t.desc;
                }}
            }}
            if (pricingTiers.length > 0) {{
                return pricingTiers[pricingTiers.length - 1].desc;
            }}
            return "Đơn giá chưa xác định";
        }}

        function updateUI() {{
            let hh = Math.floor(secondsElapsed / 3600);
            let mm = Math.floor((secondsElapsed % 3600) / 60);
            let ss = secondsElapsed % 60;
            document.getElementById("timer").innerText = 
                (hh < 10 ? "0" + hh : hh) + ":" + (mm < 10 ? "0" + mm : mm) + ":" + (ss < 10 ? "0" + ss : ss);
            
            let km = totalMeters / 1000.0;
            document.getElementById("km").innerText = km.toFixed(2);
            document.getElementById("price").innerText = calculateFareJS(km).toLocaleString('vi-VN') + " VNĐ";
            document.getElementById("rate_desc").innerText = "Đơn giá: " + getRateDescJS(km);
        }}

        function getBaseUrl() {{
            let baseUrl = window.location.href.split('?')[0];
            try {{
                if (window.top && window.top.location) {{
                    baseUrl = window.top.location.href.split('?')[0];
                }}
            }} catch (err) {{}}
            return baseUrl;
        }}

        function updatePaymentLink() {{
            const link = document.getElementById("btnPay");
            if (!link) return;
            const targetUrl = getBaseUrl()
                + "?action=checkout&dist=" + encodeURIComponent(totalMeters)
                + "&elapsed=" + encodeURIComponent(secondsElapsed)
                + "&start=" + encodeURIComponent(startTimestamp)
                + "&cname=" + encodeURIComponent(customerName)
                + "&cphone=" + encodeURIComponent(customerPhone);
            link.href = targetUrl;
        }}

        updateUI();
        updatePaymentLink();

        // TẠM DỪNG dừng cả đồng hồ và GPS; TIẾP TỤC mới chạy lại.
        setInterval(function() {{
            if (!isPaused) {{
                secondsElapsed++;
                localStorage.setItem(tripStorageKey + "_seconds", secondsElapsed);
                updateUI();
                updatePaymentLink();
            }}
        }}, 1000);

        function togglePause() {{
            vibrate(60);
            isPaused = !isPaused;
            let btn = document.getElementById("btnPause");
            let label = document.getElementById("status_label");
            if (isPaused) {{
                btn.innerText = "▶️ TIẾP TỤC";
                btn.style.background = "#2563eb";
                label.innerText = "⏸ ĐANG TẠM DỪNG GPS";
                label.style.color = "#fbbf24";
                updatePaymentLink();
                showToast("⏸ Đã tạm dừng: dừng cả đồng hồ và GPS.", "#d97706");
            }} else {{
                btn.innerText = "⏸ TẠM DỪNG";
                btn.style.background = "#d97706";
                label.innerText = "🟢 ĐỒNG HỒ TÍNH CƯỚC THỜI GIAN THỰC";
                label.style.color = "#34d399";
                updatePaymentLink();
                showToast("▶️ Tiếp tục đồng hồ và GPS.", "#059669");
            }}
        }}

        function calcCrow(lat1, lon1, lat2, lon2) {{
            var R = 6371000;
            var dLat = (lat2 - lat1) * Math.PI / 180;
            var dLon = (lon2 - lon1) * Math.PI / 180;
            var a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                Math.sin(dLon/2) * Math.sin(dLon/2);
            return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        }}

        let lastLat = null, lastLon = null;

        if ("geolocation" in navigator) {{
            navigator.geolocation.watchPosition(
                function(pos) {{
                    let lat = pos.coords.latitude, lon = pos.coords.longitude, acc = pos.coords.accuracy;
                    document.getElementById("debug_acc").innerText = "Độ chính xác GPS: ±" + acc.toFixed(1) + "m";
                    
                    if (acc > {GPS_ACCURACY_MAX_M}) {{
                        document.getElementById("debug_acc").innerText = "GPS: tín hiệu yếu (±" + acc.toFixed(1) + "m), chưa cộng quãng đường";
                        return;
                    }}
                    if (lastLat === null) {{ lastLat = lat; lastLon = lon; return; }}
                    
                    if (!isPaused) {{
                        let d = calcCrow(lastLat, lastLon, lat, lon);
                        if (d >= {MIN_MOVE_M} && d < 120) {{
                            totalMeters += d;
                            localStorage.setItem(tripStorageKey + "_meters", totalMeters);
                            updateUI();
                        }}
                    }}
                    lastLat = lat; lastLon = lon;
                }},
                err => {{ document.getElementById("debug_acc").innerText = "Lỗi GPS: Vui lòng bật định vị điện thoại!"; }},
                {{ enableHighAccuracy: true, maximumAge: 0, timeout: 15000 }}
            );
        }}

        // Fallback cho một số trình duyệt chặn target="_top" trong iframe.
        const paymentLink = document.getElementById("btnPay");
        if (paymentLink) {{
            paymentLink.addEventListener("click", function(e) {{
                vibrate(90);
                const targetUrl = paymentLink.href;
                showToast("Đang chuyển sang xác nhận thanh toán...", "#059669");
                setTimeout(function() {{
                    try {{
                        window.top.location.href = targetUrl;
                    }} catch (err) {{
                        window.location.href = targetUrl;
                    }}
                }}, 80);
            }});
        }}
        </script>
        """
        components.html(html_live_tracker, height=310)

# ============================================================
# CỬA SỔ 3: XÁC NHẬN THANH TOÁN + HÓA ĐƠN
# ============================================================
elif st.session_state["step"] == 3:
    start_ts = st.session_state.get("trip_started_at") or time.time()
    end_ts = st.session_state.get("final_end_ts") or time.time()
    dist_val = max(0.0, float(st.session_state.get("final_dist", 0.0)))
    cname = st.session_state.get("cust_name", "Khách vãng lai")
    cphone = st.session_state.get("cust_phone", "")
    trip_id = st.session_state.get("trip_id", "")

    start_time_str = get_vn_time(start_ts)
    end_time_str = get_vn_time(end_ts)
    time_diff = max(0, int(st.session_state.get("final_elapsed", 0)))
    if time_diff == 0 and end_ts and start_ts:
        # Tương thích với các cuốc cũ nếu chưa truyền elapsed.
        time_diff = max(0, int(end_ts - start_ts))
    hh, mm, ss = time_diff // 3600, (time_diff % 3600) // 60, time_diff % 60
    total_time_str = f"{hh:02d}:{mm:02d}:{ss:02d}"

    km_val = round(dist_val / 1000.0, 2)
    fare_val = calculate_fare(km_val)
    driver_name_val = st.session_state.get('user_name', 'Tài xế')
    unit_desc = get_current_unit_price_desc(km_val)

    # ------------------------------------------------------------
    # BƯỚC 1: XÁC NHẬN THANH TOÁN
    # ------------------------------------------------------------
    if st.session_state.get("payment_pending", False):
        st.markdown(
            f"""
            <div class="pro-card" style="border: 2px solid #059669; background: linear-gradient(180deg,#ffffff 0%,#f0fdf4 100%);">
                <div style="text-align:center;">
                    <div style="font-size:38px;">💵</div>
                    <div style="font-size:22px; font-weight:900; color:#064e3b;">XÁC NHẬN THANH TOÁN</div>
                    <div style="font-size:13px; color:#64748b; font-weight:700; margin-top:3px;">Mã cuốc: {safe_html(trip_id)}</div>
                </div>
                <div style="margin-top:14px; background:#fff; border-radius:16px; padding:14px; border:1px solid #d1fae5;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px;"><span style="color:#64748b;">Khách hàng</span><b>{safe_html(cname)}</b></div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:8px;"><span style="color:#64748b;">Quãng đường</span><b>{km_val:.2f} km</b></div>
                    <div style="display:flex; justify-content:space-between;"><span style="color:#64748b;">Thời gian</span><b>{total_time_str}</b></div>
                </div>
                <div style="text-align:center; margin-top:15px;">
                    <div style="font-size:12px; color:#64748b; font-weight:800; text-transform:uppercase;">SỐ TIỀN KHÁCH CẦN THANH TOÁN</div>
                    <div style="font-size:40px; font-weight:900; color:#059669; margin-top:2px;">{format(fare_val, ',')} VNĐ</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        payment_method = st.radio(
            "Chọn phương thức thanh toán:",
            ["💵 TIỀN MẶT", "🏦 CHUYỂN KHOẢN"],
            index=0,
            key="payment_method_selector",
        )
        selected_method = "Tiền mặt" if payment_method.startswith("💵") else "Chuyển khoản"
        st.session_state["payment_method"] = selected_method

        st.markdown(
            "<div style='font-size:13px; color:#475569; font-weight:700; margin:8px 2px 12px;'>"
            "⚠️ Chỉ xác nhận sau khi bác đã thực nhận đủ tiền từ khách.</div>",
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("↩️ QUAY LẠI", use_container_width=True):
                # Giữ cuốc đang chạy để bác quay lại màn hình GPS nếu bấm nhầm.
                st.session_state["payment_pending"] = False
                st.session_state["step"] = 2
                st.rerun()
        with col2:
            if st.button("✅ XÁC NHẬN ĐÃ NHẬN TIỀN", use_container_width=True):
                st.session_state["payment_confirmed"] = True
                st.session_state["payment_pending"] = False
                st.rerun()

        st.stop()

    # ------------------------------------------------------------
    # BƯỚC 2: GHI NHẬN GIAO DỊCH VÀ HIỂN THỊ HÓA ĐƠN
    # ------------------------------------------------------------
    payment_method = st.session_state.get("payment_method") or "Tiền mặt"

    if not st.session_state["saved_to_sheet"]:
        if trip_exists_in_sheet("DATA_4567", trip_id):
            save_ok = True
        else:
            stt = get_next_stt("DATA_4567")
            row_data = [
                stt, trip_id, start_time_str, end_time_str, total_time_str,
                cname, cphone, fare_val, driver_name_val,
                unit_desc, km_val, fare_val, "ĐÃ THANH TOÁN"
            ]
            save_ok = append_row_to_sheet("DATA_4567", row_data)

        if save_ok:
            # Phương thức thanh toán được ghi vào cột riêng; nếu chưa có cột, app tự tạo.
            method_ok = set_payment_method_in_sheet("DATA_4567", trip_id, payment_method)
            cache_deleted = delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)
            if method_ok and cache_deleted:
                st.session_state["saved_to_sheet"] = True
            elif method_ok and not cache_deleted:
                # DATA đã tồn tại và phương thức đã được ghi; không coi việc xóa cache thất bại là mất giao dịch.
                st.session_state["saved_to_sheet"] = True
            else:
                st.error("❌ Giao dịch đã tạo nhưng chưa ghi được phương thức thanh toán. Vui lòng kiểm tra Google Sheets.")
        else:
            st.error("❌ Chưa thể đồng bộ hóa đơn lên DATA_4567. Vui lòng giữ nguyên màn hình này và thử lại.")

    if st.session_state["saved_to_sheet"]:
        st.success(f"✅ Đã xác nhận thanh toán bằng **{payment_method}** và đồng bộ dữ liệu.")

    # Nút quay về màn hình chính
    if st.button("⬅️ QUAY LẠI MÀN HÌNH CHÍNH", use_container_width=True):
        update_driver_status(st.session_state["user_phone"], "Trực tuyến")
        st.session_state["trip_active_state"] = False
        st.session_state["saved_to_sheet"] = False
        st.session_state["payment_pending"] = False
        st.session_state["payment_method"] = ""
        st.session_state["payment_confirmed"] = False
        st.session_state["final_elapsed"] = 0
        st.session_state["step"] = 2
        st.rerun()

    # Hóa đơn
    cname_html_invoice = safe_html(cname)
    cphone_html_invoice = safe_html(cphone) if cphone else "Không có SĐT"
    trip_id_html = safe_html(trip_id)
    start_time_html = safe_html(start_time_str)
    end_time_html = safe_html(end_time_str)
    total_time_html = safe_html(total_time_str)
    unit_desc_html = safe_html(unit_desc)
    driver_name_html = safe_html(driver_name_val)
    payment_method_html = safe_html(payment_method)

    invoice_html = f"""
    <div style="font-family: system-ui, -apple-system, sans-serif; padding: 2px;">
        <div style="background: #ffffff; border-radius: 20px; padding: 18px 20px; border: 2px solid #059669; box-shadow: 0 10px 25px rgba(0,0,0,0.05); margin-bottom: 12px;">
            <div style="text-align: center; border-bottom: 2px dashed #cbd5e1; padding-bottom: 12px; margin-bottom: 12px;">
                <div style="font-size: 32px;">🧾</div>
                <div style="font-size: 19px; font-weight: 900; color: #064e3b; margin-top: 4px;">HÓA ĐƠN CHI TIẾT CHUYẾN ĐI</div>
                <div style="font-size: 12px; color: #64748b; font-weight: 700; margin-top: 2px;">Mã cuốc: {trip_id_html}</div>
            </div>
            <div style="font-size: 14px; color: #334155; line-height: 1.7;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;"><span style="color: #64748b; font-weight: 600;">Khách hàng:</span><span style="font-weight: 800; color: #0f172a; text-align: right;">{cname_html_invoice} ({cphone_html_invoice})</span></div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;"><span style="color: #64748b; font-weight: 600;">Tài xế:</span><span style="font-weight: 800; color: #0f172a;">{driver_name_html}</span></div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;"><span style="color: #64748b; font-weight: 600;">Giờ khởi hành:</span><span style="font-weight: 700; color: #0f172a;">{start_time_html}</span></div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;"><span style="color: #64748b; font-weight: 600;">Giờ kết thúc:</span><span style="font-weight: 700; color: #0f172a;">{end_time_html}</span></div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;"><span style="color: #64748b; font-weight: 600;">Thời gian đi:</span><span style="font-weight: 700; color: #0f172a;">{total_time_html}</span></div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;"><span style="color: #64748b; font-weight: 600;">Quãng đường:</span><span style="font-weight: 800; color: #059669;">{km_val:.2f} km</span></div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;"><span style="color: #64748b; font-weight: 600;">Mức giá:</span><span style="font-weight: 700; color: #d97706; font-size: 13px; text-align: right;">{unit_desc_html}</span></div>
                <div style="display: flex; justify-content: space-between;"><span style="color: #64748b; font-weight: 600;">Thanh toán:</span><span style="font-weight: 800; color: #059669;">{payment_method_html}</span></div>
            </div>
            <div style="margin-top: 14px; padding-top: 12px; border-top: 2px dashed #cbd5e1; text-align: center;">
                <div style="font-size: 12px; color: #64748b; font-weight: 700; text-transform: uppercase;">Tổng thành tiền</div>
                <div style="font-size: 36px; font-weight: 900; color: #059669; margin-top: 2px;">{format(fare_val, ',')} VNĐ</div>
                <div style="font-size: 11px; color: #10b981; font-weight: 700; margin-top: 2px;">✅ Đã thanh toán & đồng bộ lên Google Sheets</div>
            </div>
        </div>
    </div>
    """
    components.html(invoice_html, height=560)
