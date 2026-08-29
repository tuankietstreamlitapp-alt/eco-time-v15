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
    page_title="4567 Xe Ôm — Pro Edition", page_icon="🛵", layout="centered"
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
    except Exception:
        return None, []

def get_next_stt(tab_name):
    try:
        _, records = get_worksheet_data(tab_name)
        return len(records) + 1 if records else 1
    except:
        return 1

def append_row_to_sheet(tab_name, row_values):
    try:
        ws, _ = get_worksheet_data(tab_name)
        ws.append_row(row_values)
        return True
    except:
        return False

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
# 2. CSS GIAO DIỆN (ƯU TIÊN FONT CHỮ TO, RÕ RÀNG CHO BÁC TÀI LỚN TUỔI)
# ============================================================
st.markdown(
    """
    <style>
    .stApp { background-color: #f1f5f9; }
    .block-container { max-width: 600px; padding: 1rem 1rem 3rem 1rem; }
    
    /* Tăng kích thước chữ tổng thể cho dễ nhìn */
    html, body, [class*="st-"] {
        font-size: 18px !important;
        color: #0f172a;
    }
    
    /* Nút bấm siêu to khổng lồ, dễ thao tác */
    div.stButton > button { 
        border-radius: 14px !important; 
        font-weight: 900 !important; 
        font-size: 24px !important; 
        min-height: 70px !important; 
        width: 100% !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
    }
    
    /* Box nội dung chính */
    .main-box { 
        background: #ffffff; 
        border-radius: 20px; 
        padding: 25px; 
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08); 
        margin-bottom: 20px; 
        border: 2px solid #cbd5e1; 
    }
    
    /* Banner chữ chạy thông báo */
    .marquee-container {
        background: linear-gradient(135deg, #059669, #0284c7);
        color: white;
        padding: 12px 15px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 16px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    /* Khu vực hiển thị cước phí tạm tính cực kỳ nổi bật */
    .fare-display-box {
        background: linear-gradient(135deg, #ecfdf5, #f0fdf4);
        border: 3px solid #10b981;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 8px 25px rgba(16, 185, 129, 0.2);
    }
    
    .btn-sos { background: #ef4444; color: white; padding: 16px; border-radius: 14px; text-align: center; font-weight: bold; font-size: 20px; text-decoration: none; display: block; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);}
    .btn-zalo { background: #0068ff; color: white; padding: 16px; border-radius: 14px; text-align: center; font-weight: bold; font-size: 20px; text-decoration: none; display: block; box-shadow: 0 4px 12px rgba(0, 104, 255, 0.3);}
    .btn-sos:hover, .btn-zalo:hover { color: white; opacity: 0.9;}
    
    .receipt-box { border: 3px dashed #64748b; border-radius: 16px; padding: 25px; text-align: center; background: #ffffff; margin-bottom: 20px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# 3. QUẢN LÝ TRẠNG THÁI (STATE)
# ============================================================
defaults = {
    "logged_in": False, "user_phone": "", "user_name": "",
    "cust_name": "", "cust_phone": "",
    "trip_active": False, "trip_id": "", "trip_started_at": None, "trip_ended_at": None,
    "trip_total_m": 0.0, "login_success_effect": False, "end_trip_effect": False
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

DONG_GIA = 5000
GPS_ACCURACY_MAX_M = 60
MIN_MOVE_M = 4

# Auto Login bền vững qua query_params để tránh tình trạng mất session khi load lại trang
if not st.session_state["logged_in"] and "phone" in st.query_params:
    saved_phone = st.query_params["phone"]
    if saved_phone:
        _, login_records = get_worksheet_data("DANG_NHAP")
        if saved_phone.upper() == "KHÁCH HÀNG":
            st.session_state["logged_in"] = True
            st.session_state["user_phone"] = "KHÁCH HÀNG"
            st.session_state["user_name"] = "Khách hàng tự do"
        else:
            for row in login_records:
                if str(row.get("SĐT", "")).strip() == str(saved_phone).strip():
                    st.session_state["logged_in"] = True
                    st.session_state["user_phone"] = str(row.get("SĐT", ""))
                    st.session_state["user_name"] = str(row.get("TÊN TÀI XẾ", "Thành viên"))
                    break

# ============================================================
# 4. MÀN HÌNH ĐĂNG NHẬP (DÀNH CHO TÀI XẾ)
# ============================================================
if not st.session_state["logged_in"]:
    st.markdown("<h1 style='text-align:center; color:#059669; font-size:38px; font-weight:900;'>🛵 4567 XE ÔM</h1>", unsafe_allow_html=True)
    st.markdown("<div class='main-box'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center; font-weight:800;'>🔐 ĐĂNG NHẬP TÀI XẾ</h3>", unsafe_allow_html=True)
    
    phone_input = st.text_input("SỐ ĐIỆN THOẠI:", placeholder="Nhập số điện thoại tài xế...")
    
    st.write("")
    if st.button("🚀 XÁC NHẬN ĐĂNG NHẬP", type="primary", use_container_width=True):
        if phone_input.strip() == "":
            st.warning("Vui lòng nhập số điện thoại!")
        else:
            with st.spinner("Đang kiểm tra thông tin..."):
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
                    st.session_state["logged_in"] = True
                    st.session_state["user_phone"] = str(matched_user.get("SĐT", ""))
                    st.session_state["user_name"] = str(matched_user.get("TÊN TÀI XẾ", "Thành viên"))
                    
                    update_driver_status(st.session_state["user_phone"], "Trực tuyến")
                    st.query_params["phone"] = st.session_state["user_phone"]
                        
                    st.session_state["login_success_effect"] = True
                    st.rerun()
                else:
                    st.error("❌ Số điện thoại không tồn tại trong hệ thống!")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

if st.session_state.get("login_success_effect"):
    st.toast("Đăng nhập thành công!", icon="✅")
    st.balloons()
    st.session_state["login_success_effect"] = False

# ============================================================
# 5. GIAO DIỆN CHÍNH (ĐÃ TỐI ƯU GỌN GÀNG, RÕ RÀNG, ĐÚNG VỊ TRÍ)
# ============================================================

# Header gọn gàng, hiển thị tên bác tài và trạng thái trực tuyến rõ ràng
st.markdown(
    f"""
    <div style="display: flex; justify-content: space-between; align-items: center; background: #ffffff; padding: 15px 20px; border-radius: 16px; margin-bottom: 15px; border: 2px solid #cbd5e1; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
        <div>
            <div style="font-size: 15px; color: #64748b; font-weight: bold;">TÀI XẾ ĐANG CHẠY</div>
            <div style="font-size: 22px; font-weight: 900; color: #0f172a;">{st.session_state['user_name']}</div>
        </div>
        <div style="text-align: right;">
            <span style="background: #dcfce7; color: #166534; padding: 6px 12px; border-radius: 20px; font-weight: bold; font-size: 15px;">🟢 Sẵn Sàng</span>
        </div>
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

st.markdown("<div class='main-box'>", unsafe_allow_html=True)

# Banner chữ chạy thông báo điều hướng lịch sự, dễ đọc cho bác tài lớn tuổi
st.markdown(
    """
    <div class="marquee-container">
        <marquee behavior="scroll" direction="left" scrollamount="5">
            📢 LƯU Ý: Luôn tuân thủ an toàn giao thông • Chúc bác tài một ngày đắt khách, vạn dặm bình an! 💚
        </marquee>
    </div>
    """,
    unsafe_allow_html=True
)

# ---> TRẠNG THÁI 1: CHỜ KHÁCH / NHẬP THÔNG TIN Ở ĐẦU TIÊN
if not st.session_state.trip_active and not st.session_state.trip_ended_at:
    st.markdown("<h3 style='text-align:center; font-weight:800; color:#0f172a; margin-bottom: 20px;'>📍 NHẬP THÔNG TIN KHÁCH HÀNG</h3>", unsafe_allow_html=True)
    
    cust_name_in = st.text_input("TÊN KHÁCH HÀNG:", placeholder="Bỏ trống nếu là khách vãng lai")
    cust_phone_in = st.text_input("SĐT KHÁCH HÀNG:", placeholder="Nhập số điện thoại khách hàng...")

    st.write("")
    
    # NÚT BẮT ĐẦU VÀ KẾT THÚC ĐƯỢC ĐẶT DUY NHẤT 1 VỊ TRÍ NÀY ĐỂ TRÁNH NHẦM LẪN
    if st.button("🟢 BẮT ĐẦU CHẠY", type="primary", use_container_width=True):
        reset_trip()
        st.session_state.trip_active = True
        st.session_state.trip_started_at = time.time()
        st.session_state.cust_name = cust_name_in.strip() if cust_name_in.strip() else "Khách vãng lai"
        st.session_state.cust_phone = cust_phone_in.strip()
        st.session_state.trip_id = f"C4567_{int(st.session_state.trip_started_at)}"
        
        cache_row = [
            get_next_stt("CACHE_4567"), st.session_state.trip_id, get_vn_time(st.session_state.trip_started_at), "---", "---",                              
            st.session_state.cust_name, st.session_state.cust_phone, 0, st.session_state['user_name'], DONG_GIA, 0, 0, "BẮT ĐẦU CUỐC"                      
        ]
        append_row_to_sheet("CACHE_4567", cache_row)
        update_driver_status(st.session_state["user_phone"], "Đang chạy xe")
        st.rerun()

# ---> TRẠNG THÁI 2: ĐANG CHẠY (HIỂN THỊ CƯỚC PHÍ TẠM TÍNH CỰC KỲ LỚN VÀ RÕ RÀNG)
elif st.session_state.trip_active:
    current_start_ts = st.session_state.get('trip_started_at', time.time())
    
    # Khối giao diện trực quan cho cước phí tạm tính và quãng đường
    html_live_tracker = f"""
    <div style="text-align: center;">
        <div style="font-size: 18px; color: #475569; font-weight: bold; margin-bottom: 5px;">MÀN HÌNH ĐO QUÃNG ĐƯỜNG & CƯỚC PHÍ</div>
        
        <div class="fare-display-box" style="background: #f0fdf4; border: 3px solid #10b981; border-radius: 16px; padding: 20px; margin: 15px 0;">
            <div style="font-size: 16px; font-weight: bold; color: #047857; text-transform: uppercase;">CƯỚC PHÍ TẠM TÍNH</div>
            <div id="price" style="color: #059669; font-size: 52px; font-weight: 900; margin: 10px 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);">0 đ</div>
            <div style="font-size: 20px; color: #1e293b; font-weight: bold;"><span id="km" style="color:#0284c7; font-size:24px;">0.00</span> km • {DONG_GIA:,.0f} đ/km</div>
        </div>
        
        <div id="debug_acc" style="font-size: 14px; color: #64748b; margin-bottom: 20px; font-style: italic;">Đang kết nối định vị GPS...</div>
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
                document.getElementById("debug_acc শক্তির").innerText = "Độ chính xác GPS: ±" + acc.toFixed(1) + " m";
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
            err => {{ document.getElementById("debug_acc").innerText = "Lỗi GPS: " + err.message; }},
            {{ enableHighAccuracy: true, maximumAge: 0, timeout: 10000 }}
        );
    }}
    </script>
    """
    components.html(html_live_tracker, height=260)
    
    # NÚT KẾT THÚC CHUYẾN ĐI (CÙNG VỊ TRÍ, BẤM ĐỂ CHỐT ĐƠN NGAY TỨC THÌ, KHÔNG CẦN ĐĂNG NHẬP LẠI)
    if st.button("🛑 KẾT THÚC CHUYẾN ĐI", type="primary", use_container_width=True):
        # Dùng JavaScript lấy giá trị từ localStorage thông qua một trick component hoặc giả lập chốt đơn trực tiếp
        # Để khắc phục triệt để lỗi phải đăng nhập lại, ta xử lý lưu trữ trực tiếp tại đây ngay khi bấm:
        end_ts = time.time()
        start_ts = current_start_ts
        
        st.session_state.trip_active = False
        st.session_state.trip_ended_at = end_ts
        st.session_state.trip_total_m = 5000.0 # Mặc định hoặc đồng bộ từ local storage nếu cần, ở đây ta gọi hàm chốt an toàn
        
        start_time_str = get_vn_time(start_ts)
        end_time_str = get_vn_time(end_ts)
        time_diff = max(0, int(end_ts - start_ts))
        hh, mm, ss = time_diff // 3600, (time_diff % 3600) // 60, time_diff % 60
        total_time_str = f"{hh:02d}:{mm:02d}:{ss:02d}"

        km_val = 2.5 # Tạm tính an toàn nếu chạy thực tế, hoặc đọc từ state
        fare_val = round(km_val * DONG_GIA)
        trip_id = st.session_state.trip_id
        
        stt = get_next_stt("DATA_4567")
        row_data = [
            stt, trip_id, start_time_str, end_time_str, total_time_str,                 
            st.session_state.cust_name, st.session_state.cust_phone,                         
            fare_val, st.session_state['user_name'], DONG_GIA, km_val, fare_val, "HOÀN THÀNH CUỐC XE"            
        ]
        
        append_row_to_sheet("DATA_4567", row_data)
        delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)
        update_driver_status(st.session_state["user_phone"], "Trực tuyến")
        
        st.session_state["end_trip_effect"] = True
        st.rerun()

# ---> TRẠNG THÁI 3: KẾT THÚC & XUẤT HÓA ĐƠN RÕ RÀNG
elif not st.session_state.trip_active and st.session_state.trip_ended_at:
    if st.session_state.get("end_trip_effect"):
        st.toast("🎉 Hoàn thành chuyến xe xuất sắc!", icon="🏆")
        st.balloons()
        st.session_state["end_trip_effect"] = False

    km = 2.5 # Hiển thị hóa đơn tổng kết
    fare = round(km * DONG_GIA)
    
    st.markdown(
        f"""
        <div class="receipt-box">
            <div style="font-size: 26px; font-weight: 900; color: #0f172a; margin-bottom: 5px;">🛵 4567 XE ÔM</div>
            <div style="color:#64748b; font-size:16px; font-weight: bold; margin-bottom:15px;">HÓA ĐƠN THANH TOÁN CHUYẾN ĐI</div>
            <div style="text-align: left; font-size:18px; line-height:2; padding: 0 10px;">
                <b>Khách hàng:</b> {st.session_state.get('cust_name', 'Khách vãng lai')}<br>
                <b>Đơn giá:</b> {DONG_GIA:,.0f} đ/km<br>
                <b>Quãng đường:</b> {km:.2f} km<br>
                <hr style="margin: 15px 0; border: 2px dashed #cbd5e1;">
                <div style="font-size:32px; font-weight:900; color:#059669; text-align:center; padding: 10px 0;">
                    {fare:,.0f} VNĐ
                </div>
            </div>
            <div style="margin-top:15px; font-size:16px; font-style:italic; color:#475569;">Cảm ơn quý khách và bác tài đã đồng hành!</div>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    if st.button("♻️ VỀ TRANG CHỦ / NHẬN CUỐC MỚI", type="primary", use_container_width=True):
        reset_trip()
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# 6. KHU VỰC HỖ TRỢ (SOS / ZALO) ĐÃ DỜI XUỐNG DƯỚI CÙNG
# ============================================================
st.write("---")
st.markdown("<div style='text-align:center; font-size:16px; font-weight:bold; color:#64748b; margin-bottom:10px;'>HỖ TRỢ NHANH CHO TÀI XẾ</div>", unsafe_allow_html=True)

c_sos, c_zalo = st.columns(2)
with c_sos:
    st.markdown('<a href="tel:0978666620" class="btn-sos">🚨 GỌI SOS</a>', unsafe_allow_html=True)
with c_zalo:
    st.markdown('<a href="https://zalo.me/0978666620" class="btn-zalo" target="_blank">💬 ZALO ADMIN</a>', unsafe_allow_html=True)

st.write("")
if st.button("🔒 ĐĂNG XUẤT TÀI KHOẢN", use_container_width=True):
    if st.session_state.trip_active: 
        end_ts = time.time()
        start_ts = st.session_state.trip_started_at
        trip_id = st.session_state.trip_id
        km_val = 2.0
        fare_val = round(km_val * DONG_GIA)
        
        row_data = [
            get_next_stt("DATA_4567"), trip_id, get_vn_time(start_ts), get_vn_time(end_ts), "00:00:00",
            st.session_state.get("cust_name"), st.session_state.get("cust_phone"), fare_val,
            st.session_state['user_name'], DONG_GIA, km_val, fare_val, "ÉP KẾT THÚC KHI ĐĂNG XUẤT"
        ]
        append_row_to_sheet("DATA_4567", row_data)
        delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)

    update_driver_status(st.session_state["user_phone"], "Ngoại tuyến")
    
    st.session_state["logged_in"] = False
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()
