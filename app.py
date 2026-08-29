import datetime
import math
import time
import os
import gspread
import pandas as pd
import pytz
import streamlit as st
import streamlit.components.v1 as components
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="4567 Xe Ôm", page_icon="🛵", layout="centered"
)

# ============================================================
# 1. CẤU HÌNH HỆ THỐNG & GOOGLE SHEETS
# ============================================================
def get_vn_time(timestamp=None):
    vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    if timestamp is None:
        return datetime.datetime.now(vn_tz).strftime('%Y-%m-%d %H:%M:%S')
    return datetime.datetime.fromtimestamp(timestamp, vn_tz).strftime('%Y-%m-%d %H:%M:%S')

SHEET_KEY = st.secrets["connections"]["gsheets"].get("spreadsheet", "1A3-1am25vZLN57SD7pkfxxQtymCaPnCj9HgBpw5RcTY")

@st.cache_resource
def init_google_sheet_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["connections"]["gsheets"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

def get_worksheet_data(tab_name):
    try:
        client = init_google_sheet_client()
        sheet = client.open_by_key(SHEET_KEY)
        ws = sheet.worksheet(tab_name)
        return ws, ws.get_all_records()
    except Exception as e:
        print(f"Google Sheets - lỗi đọc {tab_name}: {type(e).__name__}: {e}")
        return None, []

def get_next_stt(tab_name):
    try:
        client = init_google_sheet_client()
        sheet = client.open_by_key(SHEET_KEY)
        ws = sheet.worksheet(tab_name)
        records = ws.get_all_records()
        return len(records) + 1 if records else 1
    except Exception as e:
        print(f"Google Sheets - lỗi lấy STT {tab_name}: {type(e).__name__}: {e}")
        return None

def append_row_to_sheet(tab_name, row_values):
    try:
        client = init_google_sheet_client()
        sheet = client.open_by_key(SHEET_KEY)
        ws = sheet.worksheet(tab_name)

        ws.append_row(row_values, value_input_option="USER_ENTERED")
        return True, None
    except Exception as e:
        error_msg = f"Lỗi ghi sheet {tab_name}: {type(e).__name__}: {e}"
        print(error_msg)
        return False, error_msg

def show_sheet_write_error(tab_name, error):
    st.error(f"❌ Không thể ghi dữ liệu vào {tab_name}.\n\nChi tiết: {error}")

def delete_row_from_sheet(tab_name, col_name, target_val):
    try:
        ws, records = get_worksheet_data(tab_name)
        for i, row in enumerate(records, start=2):
            if str(row.get(col_name, "")) == str(target_val):
                ws.delete_rows(i)
                return True
    except:
        pass
    return False

def update_driver_status(phone, status):
    if phone == "KHÁCH HÀNG": return
    try:
        ws, records = get_worksheet_data("DANG_NHAP")
        if not ws: return
        headers = ws.row_values(1)
        if "HIỆN TRẠNG TÀI XẾ" not in headers: return
        col_idx = headers.index("HIỆN TRẠNG TÀI XẾ") + 1
        
        for i, row in enumerate(records):
            if str(row.get("SĐT", "")).strip() == str(phone).strip():
                ws.update_cell(i + 2, col_idx, status)
                break
    except Exception:
        pass

# ============================================================
# 2. CSS GIAO DIỆN (CHỮ TO, RÕ RÀNG CHO BÁC TÀI LỚN TUỔI)
# ============================================================
st.markdown(
    """
    <style>
    .stApp { background-color: #f8fafc; }
    .block-container { max-width: 600px; padding: 0.75rem 1rem 2.5rem 1rem; }
    
    /* Làm to nhãn (label) của ô nhập liệu */
    .stTextInput label { font-size: 18px !important; font-weight: bold !important; color: #334155; }
    .stTextInput input { font-size: 18px !important; padding: 12px !important; }
    
    /* Nút bấm siêu to khổng lồ dùng chung vị trí */
    div.stButton > button { 
        border-radius: 12px !important; 
        font-weight: 900 !important; 
        font-size: 24px !important; 
        min-height: 75px !important; 
    }
    
    /* Box chức năng tập trung */
    .action-box { 
        background: #ffffff; border-radius: 16px; padding: 20px; 
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08); 
        margin-bottom: 20px; border: 2px solid #e2e8f0; 
    }
    
    /* Nút SOS / Zalo ở cuối */
    .btn-sos { background: #ef4444; color: white; padding: 15px; border-radius: 12px; text-align: center; font-weight: bold; font-size: 18px; text-decoration: none; display: block; box-shadow: 0 4px 10px rgba(239, 68, 68, 0.3);}
    .btn-zalo { background: #0068ff; color: white; padding: 15px; border-radius: 12px; text-align: center; font-weight: bold; font-size: 18px; text-decoration: none; display: block; box-shadow: 0 4px 10px rgba(0, 104, 255, 0.3);}
    .btn-sos:hover, .btn-zalo:hover { color: white; opacity: 0.9;}
    
    /* Header gọn gàng */
    .header-container { text-align: center; padding: 6px 0 12px 0; border-bottom: 2px solid #e2e8f0; margin-bottom: 14px; }
    .header-title { color: #00A86B; font-size: 30px; font-weight: 900; margin: 0; line-height: 1.1; }
    .header-driver { font-size: 18px; color: #1e293b; font-weight: bold; margin-top: 6px; }
    .fare-label { color: #475569; font-size: 22px; font-weight: 900; text-align: center; margin-top: 2px; }
    .fare-value { color: #059669; font-size: 64px; font-weight: 900; line-height: 1.05; text-align: center; margin: 4px 0 6px 0; }
    .fare-distance { color: #334155; font-size: 21px; font-weight: 700; text-align: center; margin-bottom: 18px; }
    
    .receipt-box { border: 2px dashed #94a3b8; border-radius: 12px; padding: 20px; text-align: center; background: #fff; margin-bottom: 15px;}
    
    @media print {
        body * { visibility: hidden; }
        .receipt-print-area, .receipt-print-area * { visibility: visible; }
        .receipt-print-area { position: absolute; left: 0; top: 0; width: 100%; }
        .stButton, .btn-sos, .btn-zalo { display: none !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# 3. QUẢN LÝ TRẠNG THÁI
# ============================================================
defaults = {
    "logged_in": False, "user_phone": "", "user_name": "",
    "cust_name": "", "cust_phone": "",
    "trip_active": False, "trip_id": "", "trip_started_at": None, "trip_ended_at": None,
    "trip_total_m": 0.0, "trip_status": "Chưa bắt đầu",
    "login_success_effect": False, "end_trip_effect": False
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

DONG_GIA = 5000
GPS_ACCURACY_MAX_M = 60
MIN_MOVE_M = 4

# ============================================================
# 4. PHỤC HỒI PHIÊN & XỬ LÝ KẾT THÚC CHUYẾN
# ============================================================
def restore_login_from_phone(phone):
    phone = str(phone or '').strip()
    if not phone:
        return False
    if phone.upper() == "KHÁCH HÀNG":
        st.session_state["logged_in"] = True
        st.session_state["user_phone"] = "KHÁCH HÀNG"
        st.session_state["user_name"] = "Khách hàng tự do"
        return True
    _, login_records = get_worksheet_data("DANG_NHAP")
    for row in login_records:
        if str(row.get("SĐT", "")).strip() == phone:
            st.session_state["logged_in"] = True
            st.session_state["user_phone"] = str(row.get("SĐT", "")).strip()
            st.session_state["user_name"] = str(row.get("TÊN TÀI XẾ", "Thành viên"))
            return True
    return False


def trip_already_saved(trip_id):
    try:
        _, records = get_worksheet_data("DATA_4567")
        return any(str(row.get("MÃ CUỐC XE", "")).strip() == str(trip_id).strip() for row in records)
    except Exception as e:
        print(f"Google Sheets - lỗi kiểm tra trùng {trip_id}: {type(e).__name__}: {e}")
        return False


# QUAN TRỌNG: action=stop được xử lý TRƯỚC màn hình đăng nhập.
# Khi iframe điều hướng URL, Streamlit có thể tạo phiên mới; nếu để
# màn hình đăng nhập chạy trước thì tài xế bị văng ra ngoài và không thấy bill.
if st.query_params.get("action") == "stop":
    action_phone = st.query_params.get("phone", "")
    if not st.session_state.get("logged_in") and not restore_login_from_phone(action_phone):
        st.error("❌ Không xác định được tài xế để hoàn tất cuốc xe. Vui lòng kiểm tra lại SĐT đăng nhập.")
        st.stop()

    try:
        dist_val = max(0.0, float(st.query_params.get("dist", 0.0)))
    except (TypeError, ValueError):
        dist_val = 0.0
    try:
        start_ts = float(st.query_params.get("start", time.time()))
    except (TypeError, ValueError):
        start_ts = time.time()

    end_ts = time.time()
    cname = str(st.query_params.get("cname", "Khách vãng lai")).replace("%20", " ")
    cphone = str(st.query_params.get("cphone", ""))
    time_diff = max(0, int(end_ts - start_ts))
    hh, mm, ss = time_diff // 3600, (time_diff % 3600) // 60, time_diff % 60
    total_time_str = f"{hh:02d}:{mm:02d}:{ss:02d}"
    km_val = round(dist_val / 1000.0, 2)
    fare_val = round(km_val * DONG_GIA)
    trip_id = f"C4567_{int(start_ts)}"

    st.session_state.trip_active = False
    st.session_state.trip_ended_at = end_ts
    st.session_state.trip_total_m = dist_val
    st.session_state.trip_status = "Đã hoàn thành"
    st.session_state.cust_name = cname
    st.session_state.cust_phone = cphone
    st.session_state.trip_id = trip_id

    # Chống ghi trùng nếu trình duyệt gửi lại URL kết thúc.
    if not trip_already_saved(trip_id):
        stt = get_next_stt("DATA_4567")
        if stt is None:
            show_sheet_write_error("DATA_4567", "Không lấy được STT. Kiểm tra kết nối/quyền Google Sheets.")
            st.stop()
        row_data = [
            stt, trip_id, get_vn_time(start_ts), get_vn_time(end_ts), total_time_str,
            cname, cphone, fare_val, st.session_state["user_name"],
            DONG_GIA, km_val, fare_val, "HOÀN THÀNH CUỐC XE"
        ]
        data_ok, data_error = append_row_to_sheet("DATA_4567", row_data)
        if not data_ok:
            show_sheet_write_error("DATA_4567", data_error)
            st.stop()
        # Chỉ xóa CACHE sau khi DATA đã ghi thành công.
        delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)

    update_driver_status(st.session_state["user_phone"], "Trực tuyến")
    st.session_state["end_trip_effect"] = True

    for key in ["action", "dist", "start", "cname", "cphone"]:
        if key in st.query_params:
            del st.query_params[key]
    st.rerun()


# TỰ ĐỘNG ĐĂNG NHẬP THÔNG THƯỜNG
if not st.session_state["logged_in"] and "phone" in st.query_params:
    restore_login_from_phone(st.query_params.get("phone", ""))

# ============================================================
# 5. MÀN HÌNH ĐĂNG NHẬP
# ============================================================
if not st.session_state["logged_in"]:
    st.markdown("<div class='header-container'><h1 class='header-title'>🛵 4567 XE ÔM</h1></div>", unsafe_allow_html=True)
    st.markdown("<div class='action-box'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>🔐 ĐĂNG NHẬP</h3>", unsafe_allow_html=True)
    phone_input = st.text_input("SỐ ĐIỆN THOẠI TÀI XẾ:", placeholder="Nhập SĐT vào đây...")
    remember_me = st.checkbox("Lưu đăng nhập cho lần sau", value=True)
    st.write("")
    if st.button("🚀 XÁC NHẬN", type="primary", use_container_width=True):
        if phone_input.strip() == "":
            st.warning("Vui lòng nhập SĐT!")
        else:
            with st.spinner("Đang kiểm tra..."):
                _, login_records = get_worksheet_data("DANG_NHAP")
                matched_user = None
                if phone_input.upper() == "KHÁCH HÀNG":
                    matched_user = {"SĐT": "KHÁCH HÀNG", "TÊN TÀI XẾ": "Khách hàng tự do", "HIỆN TRẠNG TÀI XẾ": ""}
                else:
                    for row in login_records:
                        if str(row.get("SĐT", "")).strip() == phone_input.strip():
                            matched_user = row
                            break
                if matched_user:
                    current_status = str(matched_user.get("HIỆN TRẠNG TÀI XẾ", ""))
                    if current_status in ["Trực tuyến", "Đang chạy xe"] and matched_user.get("SĐT") != "KHÁCH HÀNG":
                        st.error("⚠️ Tài khoản đang được sử dụng trên máy khác!")
                    else:
                        st.session_state["logged_in"] = True
                        st.session_state["user_phone"] = str(matched_user.get("SĐT", ""))
                        st.session_state["user_name"] = str(matched_user.get("TÊN TÀI XẾ", "Thành viên"))
                        update_driver_status(st.session_state["user_phone"], "Trực tuyến")
                        if remember_me:
                            st.query_params["phone"] = st.session_state["user_phone"]
                        else:
                            st.query_params.clear()
                        st.session_state["login_success_effect"] = True
                        st.rerun()
                else:
                    st.error("❌ Số điện thoại không đúng!")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

if st.session_state.get("login_success_effect"):
    st.toast("Đăng nhập thành công!", icon="✅")
    st.session_state["login_success_effect"] = False

# ============================================================
# 6. GIAO DIỆN CHÍNH GỌN GÀNG
# ============================================================
# HEADER GOM GỌN
status_icon = "🟡 ĐANG CHẠY" if st.session_state.trip_active else "🟢 SẴN SÀNG"
st.markdown(
    f"""
    <div class='header-container'>
        <div class='header-title'>🛵 4567 XE ÔM</div>
        <div class='header-driver'>👤 {st.session_state['user_name']} &nbsp;•&nbsp; <span style="color:{'#d97706' if st.session_state.trip_active else '#16a34a'};">{status_icon}</span></div>
    </div>
    """, 
    unsafe_allow_html=True
)

def reset_trip():
    st.session_state.trip_active = False
    st.session_state.trip_started_at = None
    st.session_state.trip_ended_at = None
    st.session_state.trip_total_m = 0.0
    st.session_state.cust_name = ""
    st.session_state.cust_phone = ""

st.markdown("<div class='action-box'>", unsafe_allow_html=True)

# ---> TRẠNG THÁI 1: CHỜ KHÁCH
if not st.session_state.trip_active and not st.session_state.trip_ended_at:
    cust_name_in = st.text_input("TÊN KHÁCH HÀNG:", placeholder="Bỏ trống nếu là khách vãng lai")
    cust_phone_in = st.text_input("SĐT KHÁCH HÀNG:", placeholder="Nhập số điện thoại...")

    st.write("")
    if st.button("🟢 BẮT ĐẦU CHẠY", type="primary", use_container_width=True):
        reset_trip()
        st.session_state.trip_active = True
        st.session_state.trip_started_at = time.time()
        st.session_state.cust_name = cust_name_in.strip() if cust_name_in.strip() else "Khách vãng lai"
        st.session_state.cust_phone = cust_phone_in.strip()
        st.session_state.trip_id = f"C4567_{int(st.session_state.trip_started_at)}"
        
        cache_stt = get_next_stt("CACHE_4567")
        if cache_stt is None:
            show_sheet_write_error("CACHE_4567", "Không lấy được STT. Kiểm tra kết nối/quyền Google Sheets.")
            st.stop()
        cache_row = [
            cache_stt, st.session_state.trip_id, get_vn_time(st.session_state.trip_started_at), "---", "---",                              
            st.session_state.cust_name, st.session_state.cust_phone, 0, st.session_state['user_name'], DONG_GIA, 0, 0, "BẮT ĐẦU CUỐC"                      
        ]
        cache_ok, cache_error = append_row_to_sheet("CACHE_4567", cache_row)
        if not cache_ok:
            show_sheet_write_error("CACHE_4567", cache_error)
            st.stop()

        update_driver_status(st.session_state["user_phone"], "Đang chạy xe")
        st.rerun()

# ---> TRẠNG THÁI 2: ĐANG CHẠY (DOANH THU TO RÕ)
elif st.session_state.trip_active:
    current_start_ts = st.session_state.get('trip_started_at', time.time())
    
    html_live_tracker = f"""
    <div style="text-align: center;">
        <div class="fare-label">CƯỚC PHÍ TẠM TÍNH</div>
        <div id="price" class="fare-value">0 đ</div>
        <div class="fare-distance"><span id="km">0.00</span> km • {DONG_GIA:,.0f} đ/km</div>
        
        <button id="btnStop" onclick="stopTripNow()" style="width: 100%; background: #ef4444; color: white; border: none; border-radius: 12px; padding: 18px; font-size: 24px; font-weight: 900; cursor: pointer; box-shadow: 0 5px 15px rgba(239, 68, 68, 0.4);">
            🛑 KẾT THÚC
        </button>
        <div id="debug_acc" style="font-size: 14px; color: #94a3b8; margin-top: 15px;">Đang tìm vệ tinh GPS...</div>
    </div>
    <script>
    let totalMeters = parseFloat(localStorage.getItem("xeom_total_meters") || "0.0");
    const dongGia = {DONG_GIA};
    let lastLat = null, lastLon = null;

    function calcCrow(lat1, lon1, lat2, lon2) {{
        var R = 6371000;
        var dLat = (lat2 - lat1) * Math.PI / 180;
        var dLon = (lon2 - lon1) * Math.PI / 180;
        var a = Math.sin(dLat/2) * Math.sin(dLat/2) + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon/2) * Math.sin(dLon/2);
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    }}

    function updateDisplay() {{
        let km = totalMeters / 1000.0;
        document.getElementById("km").innerText = km.toFixed(2);
        document.getElementById("price").innerText = Math.round(km * dongGia).toLocaleString('vi-VN') + " đ";
    }}
    updateDisplay();

    if ("geolocation" in navigator) {{
        navigator.geolocation.watchPosition(
            function(pos) {{
                let lat = pos.coords.latitude, lon = pos.coords.longitude, acc = pos.coords.accuracy;
                document.getElementById("debug_acc").innerText = "Sai số GPS: ±" + acc.toFixed(0) + " m";
                if (acc > {GPS_ACCURACY_MAX_M}) return;
                if (lastLat === null) {{ lastLat = lat; lastLon = lon; return; }}
                let d = calcCrow(lastLat, lastLon, lat, lon);
                if (d >= {MIN_MOVE_M} && d < 150) {{
                    totalMeters += d;
                    lastLat = lat; lastLon = lon;
                    localStorage.setItem("xeom_total_meters", totalMeters);
                    updateDisplay();
                }}
            }},
            err => {{ document.getElementById("debug_acc").innerText = "Lỗi GPS: Vui lòng bật vị trí!"; }},
            {{ enableHighAccuracy: true, maximumAge: 0, timeout: 10000 }}
        );
    }}

    function stopTripNow() {{
        let btn = document.getElementById("btnStop");
        btn.innerText = "⏳ ĐANG LƯU..."; btn.style.background = "#64748b"; btn.disabled = true;
        
        let finalDist = localStorage.getItem("xeom_total_meters") || "0";
        localStorage.removeItem("xeom_total_meters");
        
        let parentUrl;
        try {{ parentUrl = new URL(window.parent.location.href); }} 
        catch(e) {{ parentUrl = new URL(window.location.href); }}
        
        parentUrl.searchParams.set("action", "stop");
        parentUrl.searchParams.set("dist", finalDist);
        parentUrl.searchParams.set("start", "{current_start_ts}");
        parentUrl.searchParams.set("cname", "{st.session_state.get('cust_name', 'Khách vãng lai')}");
        parentUrl.searchParams.set("cphone", "{st.session_state.get('cust_phone', '')}");
        
        // FIX LỖI VĂNG ĐĂNG NHẬP: Gửi kèm luôn sđt để App nhận diện ngay
        parentUrl.searchParams.set("phone", "{st.session_state.get('user_phone', '')}");
        
        try {{ window.top.location.href = parentUrl.toString(); }} 
        catch(e) {{ window.location.href = parentUrl.toString(); }}
    }}
    </script>
    """
    components.html(html_live_tracker, height=350)

# ---> TRẠNG THÁI 3: KẾT THÚC (HIỂN THỊ HÓA ĐƠN)
elif not st.session_state.trip_active and st.session_state.trip_ended_at:
    if st.session_state.get("end_trip_effect"):
        st.toast("🎉 Đã lưu doanh thu thành công!", icon="🏆")
        st.balloons()
        st.session_state["end_trip_effect"] = False

    km = st.session_state.trip_total_m / 1000.0
    fare = round(km * DONG_GIA)
    
    st.markdown("<div class='receipt-print-area'>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="receipt-box">
            <div style="font-size: 26px; font-weight: 900; color: #0f172a; margin-bottom: 5px;">HÓA ĐƠN</div>
            <div style="color:#64748b; font-size:16px; margin-bottom:15px;">Cuốc xe vừa hoàn thành</div>
            <div style="text-align: left; font-size:18px; line-height:1.8;">
                <b>Khách hàng:</b> {st.session_state.get('cust_name', 'Khách vãng lai')}<br>
                <b>Quãng đường:</b> {km:.2f} km<br>
                <hr style="margin: 15px 0; border: 1px dashed #cbd5e1;">
                <div style="font-size:48px; font-weight:900; color:#059669; text-align:center; padding: 12px 0;">
                    {fare:,.0f} đ
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)
    
    if st.button("♻️ NHẬN CUỐC MỚI", type="primary", use_container_width=True):
        reset_trip()
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# 7. KHU VỰC HỖ TRỢ VÀ ĐĂNG XUẤT DỜI XUỐNG DƯỚI CÙNG
# ============================================================
st.write("")
st.write("")
c_sos, c_zalo = st.columns(2)
with c_sos:
    st.markdown('<a href="tel:0978666620" class="btn-sos">🚨 GỌI SOS</a>', unsafe_allow_html=True)
with c_zalo:
    st.markdown('<a href="https://zalo.me/0978666620" class="btn-zalo" target="_blank">💬 ZALO ADMIN</a>', unsafe_allow_html=True)

st.write("")
if st.button("🔒 ĐĂNG XUẤT", use_container_width=True):
    if st.session_state.trip_active: 
        end_ts = time.time()
        start_ts = st.session_state.trip_started_at
        trip_id = st.session_state.trip_id
        km_val = round(st.session_state.trip_total_m / 1000.0, 2)
        fare_val = round(km_val * DONG_GIA)
        
        row_data = [
            get_next_stt("DATA_4567"), trip_id, get_vn_time(start_ts), get_vn_time(end_ts), "00:00:00",
            st.session_state.get("cust_name"), st.session_state.get("cust_phone"), fare_val,
            st.session_state['user_name'], DONG_GIA, km_val, fare_val, "ÉP KẾT THÚC KHI ĐĂNG XUẤT"
        ]
        data_ok, data_error = append_row_to_sheet("DATA_4567", row_data)
        if not data_ok:
            show_sheet_write_error("DATA_4567", data_error)
            st.stop()

        # Chỉ xóa CACHE sau khi DATA_4567 đã ghi thành công.
        delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)

    update_driver_status(st.session_state["user_phone"], "Ngoại tuyến")
    
    st.session_state["logged_in"] = False
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()
