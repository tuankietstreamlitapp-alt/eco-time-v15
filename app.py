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
    except Exception as e:
        st.error(f"Lỗi kết nối ({tab_name}): {e}")
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

# Hàm Cập nhật trạng thái tài xế cho Admin theo dõi
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
# 2. CSS GIAO DIỆN CHUYÊN NGHIỆP TỐI ƯU
# ============================================================
st.markdown(
    """
    <style>
    /* Tổng thể */
    .stApp { background-color: #f1f5f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .block-container { max-width: 600px; padding: 1.5rem 1rem 3rem 1rem; }
    
    /* Box chức năng chính */
    .glass-card { background: #ffffff; border-radius: 16px; padding: 20px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05); margin-bottom: 20px; border: 1px solid #e2e8f0; }
    
    /* Nút bấm SOS / Zalo */
    .btn-sos { background: #ef4444; color: white; padding: 10px; border-radius: 10px; text-align: center; font-weight: bold; text-decoration: none; display: block; box-shadow: 0 4px 10px rgba(239, 68, 68, 0.3); transition: 0.3s;}
    .btn-zalo { background: #0068ff; color: white; padding: 10px; border-radius: 10px; text-align: center; font-weight: bold; text-decoration: none; display: block; box-shadow: 0 4px 10px rgba(0, 104, 255, 0.3); transition: 0.3s;}
    .btn-sos:hover { background: #dc2626; color: white; }
    .btn-zalo:hover { background: #0055d4; color: white; }
    
    /* Hóa đơn in */
    .receipt-box { border: 2px dashed #94a3b8; border-radius: 12px; padding: 20px; text-align: center; background: #fff; margin-bottom: 15px;}
    .receipt-title { font-size: 20px; font-weight: 900; color: #0f172a; margin-bottom: 5px; }
    
    /* Format in ấn ẩn các thành phần thừa */
    @media print {
        body * { visibility: hidden; }
        .receipt-print-area, .receipt-print-area * { visibility: visible; }
        .receipt-print-area { position: absolute; left: 0; top: 0; width: 100%; }
        .stButton, .btn-sos, .btn-zalo { display: none !important; }
    }
    
    /* Button mặc định */
    div.stButton > button { border-radius: 12px !important; font-weight: bold !important; min-height: 48px !important; transition: 0.2s; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# 3. QUẢN LÝ TRẠNG THÁI (SESSION STATE)
# ============================================================
defaults = {
    "logged_in": False, "user_phone": "", "user_name": "",
    "cust_name": "", "cust_phone": "",
    "trip_active": False, "trip_id": "", "trip_started_at": None, "trip_ended_at": None,
    "trip_total_m": 0.0, "trip_status": "Chưa bắt đầu"
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

DONG_GIA = 5000
GPS_ACCURACY_MAX_M = 60
MIN_MOVE_M = 4

# Tự động đăng nhập từ URL params
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
# 4. MÀN HÌNH ĐĂNG NHẬP
# ============================================================
if not st.session_state["logged_in"]:
    # Hiện Logo nếu có
    if os.path.exists("Logo.png"):
        st.image("Logo.png", use_container_width=True)
    else:
        st.markdown("<h1 style='text-align:center; color:#00A86B;'>🛵 4567 XE ÔM</h1>", unsafe_allow_html=True)

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("### 🔐 Đăng nhập hệ thống")
    st.write("Vui lòng nhập SĐT tài xế đã được cấp phép.")
    
    phone_input = st.text_input("Số điện thoại tài xế:", placeholder="Ví dụ: 0978666620")
    remember_me = st.checkbox("Ghi nhớ đăng nhập (Hãy lưu lại Bookmark link sau khi ĐN)", value=True)
    
    if st.button("🚀 XÁC NHẬN ĐĂNG NHẬP", type="primary", use_container_width=True):
        if phone_input.strip() == "":
            st.warning("Vui lòng nhập số điện thoại!")
        else:
            with st.spinner("Đang kiểm tra dữ liệu..."):
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
                    # Chống 2 máy đăng nhập cùng 1 ID (Trừ acc test Khách Hàng)
                    current_status = str(matched_user.get("HIỆN TRẠNG TÀI XẾ", ""))
                    if current_status in ["Trực tuyến", "Đang chạy xe"] and matched_user.get("SĐT") != "KHÁCH HÀNG":
                        st.error("⚠️ Tài khoản này đang được đăng nhập hoặc chạy xe ở một thiết bị khác!")
                    else:
                        st.session_state["logged_in"] = True
                        st.session_state["user_phone"] = str(matched_user.get("SĐT", ""))
                        st.session_state["user_name"] = str(matched_user.get("TÊN TÀI XẾ", "Thành viên"))
                        
                        update_driver_status(st.session_state["user_phone"], "Trực tuyến")
                        
                        if remember_me:
                            st.query_params["phone"] = st.session_state["user_phone"]
                        else:
                            st.query_params.clear()
                            
                        st.toast(f"Đăng nhập thành công! Chào {st.session_state['user_name']}", icon="✅")
                        st.balloons()
                        time.sleep(1.5)
                        st.rerun()
                else:
                    st.error("❌ Số điện thoại không tồn tại trong hệ thống!")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ============================================================
# 5. XỬ LÝ KẾT THÚC CHUYẾN TỪ URL PARAMS
# ============================================================
if "action" in st.query_params and st.query_params["action"] == "stop":
    dist_val = float(st.query_params.get("dist", 0.0))
    start_ts = float(st.query_params.get("start", time.time()))
    
    st.session_state.trip_active = False
    st.session_state.trip_ended_at = time.time()
    st.session_state.trip_total_m = dist_val
    st.session_state.trip_status = "Đã hoàn thành"
    
    start_time_str = get_vn_time(start_ts)
    end_time_str = get_vn_time(st.session_state['trip_ended_at'])
    time_diff = max(0, int(st.session_state['trip_ended_at'] - start_ts))
    hh, mm, ss = time_diff // 3600, (time_diff % 3600) // 60, time_diff % 60
    total_time_str = f"{hh:02d}:{mm:02d}:{ss:02d}"

    km_val = round(dist_val / 1000.0, 2)
    fare_val = round(km_val * DONG_GIA)
    trip_id = f"C4567_{int(start_ts)}"
    
    stt = get_next_stt("DATA_4567")
    row_data = [
        stt, trip_id, start_time_str, end_time_str, total_time_str,                 
        st.session_state.get("cust_name", "Khách vãng lai"), st.session_state.get("cust_phone", ""),                         
        fare_val, st.session_state['user_name'], DONG_GIA, km_val, fare_val, "HOÀN THÀNH CUỐC XE"            
    ]
    
    append_row_to_sheet("DATA_4567", row_data)
    delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)
    update_driver_status(st.session_state["user_phone"], "Trực tuyến") # Trả về trạng thái chờ
    
    st.toast("🎉 Hoàn thành chuyến xe xuất sắc!", icon="🏆")
    st.balloons()
    
    phone_val = st.query_params.get("phone", "")
    st.query_params.clear()
    if phone_val: st.query_params["phone"] = phone_val
    st.rerun()

# ============================================================
# 6. GIAO DIỆN CHÍNH (ĐÃ QUY HOẠCH LẠI)
# ============================================================
# Header Logo + Info
col_logo, col_info = st.columns([1, 4], vertical_alignment="center")
with col_logo:
    if os.path.exists("Logo.png"):
        st.image("Logo.png", width=80)
    else:
        st.write("🛵 **4567**")
with col_info:
    st.markdown(f"**Tài xế:** {st.session_state['user_name']}<br><span style='color:green'>🟢 Đang trực tuyến</span>", unsafe_allow_html=True)

# Nút Gọi SOS & Zalo (Đưa lên trên cùng)
c_sos, c_zalo = st.columns(2)
with c_sos:
    st.markdown('<a href="tel:0978666620" class="btn-sos">🚨 GỌI SOS</a>', unsafe_allow_html=True)
with c_zalo:
    st.markdown('<a href="https://zalo.me/0978666620" class="btn-zalo" target="_blank">💬 ZALO ADMIN</a>', unsafe_allow_html=True)
st.write("")

def reset_trip():
    st.session_state.trip_active = False
    st.session_state.trip_started_at = None
    st.session_state.trip_ended_at = None
    st.session_state.trip_total_m = 0.0

# ==================== TRẠNG THÁI 1: CHỜ KHÁCH ====================
if not st.session_state.trip_active and not st.session_state.trip_ended_at:
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("### 📍 Nhận cuốc mới")
    c1, c2 = st.columns(2)
    with c1: cust_name_in = st.text_input("Tên khách:", placeholder="Khách vãng lai")
    with c2: cust_phone_in = st.text_input("SĐT khách:", placeholder="0912345678")

    if st.button("🟢 BẮT ĐẦU CUỐC XE", type="primary", use_container_width=True):
        reset_trip()
        st.session_state.trip_active = True
        st.session_state.trip_started_at = time.time()
        st.session_state.cust_name = cust_name_in.strip() if cust_name_in.strip() else "Khách vãng lai"
        st.session_state.cust_phone = cust_phone_in.strip()
        st.session_state.trip_id = f"C4567_{int(st.session_state.trip_started_at)}"
        
        # Cập nhật Cache & Trạng thái Admin
        cache_row = [
            get_next_stt("CACHE_4567"), st.session_state.trip_id, get_vn_time(st.session_state.trip_started_at), "---", "---",                              
            st.session_state.cust_name, st.session_state.cust_phone, 0, st.session_state['user_name'], DONG_GIA, 0, 0, "BẮT ĐẦU CUỐC"                      
        ]
        append_row_to_sheet("CACHE_4567", cache_row)
        update_driver_status(st.session_state["user_phone"], "Đang chạy xe")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== TRẠNG THÁI 2: ĐANG CHẠY ====================
elif st.session_state.trip_active:
    st.markdown("<div class='glass-card' style='border: 2px solid #10b981;'>", unsafe_allow_html=True)
    st.markdown("### 🟢 Đang trong hành trình")
    st.write(f"Khách: **{st.session_state.get('cust_name')}** | SĐT: **{st.session_state.get('cust_phone', '---')}**")
    
    current_start_ts = st.session_state.get('trip_started_at', time.time())
    
    html_live_tracker = f"""
    <div style="text-align: center; padding: 10px;">
        <div style="background: #f0fdf4; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
            <div style="color: #166534; font-size: 14px; font-weight: bold;">CƯỚC PHÍ TẠM TÍNH</div>
            <div id="price" style="color: #0f172a; font-size: 40px; font-weight: 900; margin: 5px 0;">0 đ</div>
            <div style="color: #475569; font-size: 14px;"><span id="km" style="font-weight:bold;">0.00</span> km • {DONG_GIA:,.0f} đ/km</div>
        </div>
        
        <button id="btnStop" onclick="stopTripNow()" style="width: 100%; background: #ef4444; color: white; border: none; border-radius: 12px; padding: 18px; font-size: 18px; font-weight: 900; cursor: pointer; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);">
            🛑 KẾT THÚC & CHỐT ĐƠN
        </button>
        <div id="debug_acc" style="font-size: 12px; color: #94a3b8; margin-top: 15px;">GPS: Đang định vị...</div>
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
                document.getElementById("debug_acc").innerText = "Sai số GPS: ±" + acc.toFixed(1) + " m";
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

    function stopTripNow() {{
        let btn = document.getElementById("btnStop");
        btn.innerText = "⏳ ĐANG XỬ LÝ..."; btn.style.background = "#64748b"; btn.disabled = true;
        let finalDist = localStorage.getItem("xeom_total_meters") || "0";
        localStorage.removeItem("xeom_total_meters");
        
        let baseUrl = window.location.href.split('?')[0];
        try {{ if (window.parent && window.parent.location) {{ baseUrl = window.parent.location.href.split('?')[0]; }} }} catch(e) {{}}
        let targetUrl = baseUrl + "?action=stop&dist=" + finalDist + "&start={current_start_ts}";
        try {{ window.top.location.href = targetUrl; }} catch(e) {{ window.location.href = targetUrl; }}
    }}
    </script>
    """
    components.html(html_live_tracker, height=260)
    st.markdown("</div>", unsafe_allow_html=True)

# ==================== TRẠNG THÁI 3: KẾT THÚC (IN BILL) ====================
elif not st.session_state.trip_active and st.session_state.trip_ended_at:
    km = st.session_state.trip_total_m / 1000.0
    fare = round(km * DONG_GIA)
    
    st.markdown("<div class='receipt-print-area'>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="receipt-box">
            <div class="receipt-title">🛵 4567 XE ÔM</div>
            <div style="color:#64748b; font-size:12px; margin-bottom:15px;">HÓA ĐƠN ĐIỆN TỬ</div>
            <div style="text-align: left; font-size:14px; line-height:1.8;">
                <b>Tài xế:</b> {st.session_state['user_name']}<br>
                <b>Khách hàng:</b> {st.session_state.get('cust_name', 'Khách vãng lai')}<br>
                <b>Đơn giá:</b> {DONG_GIA:,.0f} đ/km<br>
                <b>Quãng đường:</b> {km:.2f} km<br>
                <hr style="margin: 10px 0; border: 1px dashed #cbd5e1;">
                <div style="font-size:22px; font-weight:900; color:#0f172a; text-align:center;">
                    TỔNG TIỀN: {fare:,.0f} VNĐ
                </div>
            </div>
            <div style="margin-top:15px; font-size:11px; font-style:italic;">Cảm ơn quý khách đã sử dụng dịch vụ!</div>
        </div>
        """, unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Nút In Hóa Đơn (sử dụng Window Print của JS)
    components.html("""
        <button onclick="window.parent.print()" style="width:100%; padding:15px; background:#475569; color:white; border:none; border-radius:10px; font-size:16px; font-weight:bold; cursor:pointer;">
            🖨️ IN HÓA ĐƠN
        </button>
    """, height=60)
    
    if st.button("♻️ VỀ TRANG CHỦ / NHẬN CUỐC MỚI", type="primary", use_container_width=True):
        reset_trip()
        st.rerun()

# ============================================================
# 7. KHU VỰC QUẢN TRỊ & BÁO CÁO (CHUYỂN XUỐNG CUỐI)
# ============================================================
st.markdown("<br><hr>", unsafe_allow_html=True)

with st.expander("🛠️ DÀNH CHO ADMIN (XEM BÁO CÁO)", expanded=False):
    tab1, tab2 = st.tabs(["📦 Dữ liệu DATA", "⚡ Bộ nhớ CACHE"])
    with tab1:
        _, data_records = get_worksheet_data("DATA_4567")
        if data_records: st.dataframe(pd.DataFrame(data_records), use_container_width=True, hide_index=True)
        else: st.info("Chưa có dữ liệu.")
    with tab2:
        _, cache_records = get_worksheet_data("CACHE_4567")
        if cache_records: st.dataframe(pd.DataFrame(cache_records), use_container_width=True, hide_index=True)
        else: st.success("CACHE đang trống.")

st.write("")
# Nút đăng xuất mờ hơn, giấu xuống cuối cùng
if st.button("🔒 ĐĂNG XUẤT", use_container_width=True):
    if st.session_state.trip_active: # Xử lý ép dừng nếu đang chạy
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
        append_row_to_sheet("DATA_4567", row_data)
        delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)

    update_driver_status(st.session_state["user_phone"], "Ngoại tuyến") # Báo Off cho Admin
    
    st.session_state["logged_in"] = False
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()
