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

# Cấu hình trang luôn ở chế độ điện thoại (Centered)
st.set_page_config(
    page_title="4567 Xe Ôm — Pro Edition", page_icon="🛵", layout="centered"
)

# ============================================================
# 1. ẨN CÁC THANH CÔNG CỤ THỪA & TỐI ƯU CSS CHO BÁC TÀI
# ============================================================
st.markdown(
    """
    <style>
    /* Ẩn thanh trắng mặc định của Streamlit */
    [data-testid="stHeader"] {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    footer {display: none !important;}
    #MainMenu {display: none !important;}
    
    /* Thu gọn khoảng không thừa, ép app vừa màn hình dọc */
    .block-container { 
        padding-top: 1rem !important; 
        padding-bottom: 1rem !important; 
        max-width: 500px !important; 
    }
    
    .stApp { background-color: #f1f5f9; }
    
    /* Khung thao tác chính */
    .action-box { 
        background: #ffffff; border-radius: 16px; padding: 18px; 
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08); 
        margin-bottom: 15px; border: 1px solid #cbd5e1; 
    }
    
    /* Chữ chạy */
    .marquee-container {
        background: #00A86B; color: white; padding: 10px; border-radius: 10px;
        font-weight: bold; font-size: 15px; margin-bottom: 15px;
    }
    
    /* Nút SOS & Zalo ở đáy */
    .btn-sos { background: #ef4444; color: white; padding: 14px; border-radius: 12px; text-align: center; font-weight: bold; font-size: 16px; text-decoration: none; display: block;}
    .btn-zalo { background: #0068ff; color: white; padding: 14px; border-radius: 12px; text-align: center; font-weight: bold; font-size: 16px; text-decoration: none; display: block;}
    
    /* Hóa đơn */
    .receipt-box { border: 2px dashed #64748b; border-radius: 12px; padding: 15px; text-align: center; background: #fff;}
    
    /* Tăng kích thước chữ input cho người lớn tuổi dễ nhìn */
    input { font-size: 18px !important; font-weight: bold !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# 2. CẤU HÌNH HỆ THỐNG & GOOGLE SHEETS
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
# 3. QUẢN LÝ TRẠNG THÁI (SESSION STATE)
# ============================================================
defaults = {
    "logged_in": False, "user_phone": "", "user_name": "",
    "cust_name": "", "cust_phone": "",
    "trip_active": False, "trip_id": "", "trip_started_at": None, "trip_ended_at": None,
    "trip_total_m": 0.0
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

DONG_GIA = 5000
GPS_ACCURACY_MAX_M = 60
MIN_MOVE_M = 4

# Tự động đăng nhập qua query_params
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
    st.markdown("<h1 style='text-align:center; color:#00A86B; font-size:32px; margin-top:20px;'>🛵 4567 XE ÔM</h1>", unsafe_allow_html=True)
    st.markdown("<div class='action-box'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center; color:#1e293b; margin-bottom: 20px;'>🔐 ĐĂNG NHẬP</h3>", unsafe_allow_html=True)
    
    phone_input = st.text_input("SỐ ĐIỆN THOẠI:", placeholder="Nhập SĐT của bác tài...")
    
    if st.button("🚀 XÁC NHẬN", type="primary", use_container_width=True):
        if phone_input.strip() == "":
            st.warning("Vui lòng nhập SĐT!")
        else:
            with st.spinner("Đang kiểm tra..."):
                _, login_records = get_worksheet_data("DANG_NHAP")
                matched_user = None
                
                if phone_input.upper() == "KHÁCH HÀNG":
                    matched_user = {"SĐT": "KHÁCH HÀNG", "TÊN TÀI XẾ": "Khách hàng tự do"}
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
                    st.rerun()
                else:
                    st.error("❌ Số điện thoại không chính xác!")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ============================================================
# 5. XỬ LÝ URL ĐỂ KẾT THÚC CHUYẾN ĐI (CHUYỂN TRẠNG THÁI MƯỢT MÀ)
# ============================================================
if "action" in st.query_params and st.query_params["action"] == "stop":
    dist_val = float(st.query_params.get("dist", 0.0))
    start_ts = float(st.query_params.get("start", time.time()))
    
    st.session_state.trip_active = False
    st.session_state.trip_ended_at = time.time()
    st.session_state.trip_total_m = dist_val
    
    st.session_state.cust_name = st.query_params.get("cname", "Khách vãng lai").replace("%20", " ")
    st.session_state.cust_phone = st.query_params.get("cphone", "")
    
    start_time_str = get_vn_time(start_ts)
    end_time_str = get_vn_time(st.session_state['trip_ended_at'])
    time_diff = max(0, int(st.session_state['trip_ended_at'] - start_ts))
    hh, mm, ss = time_diff // 3600, (time_diff % 3600) // 60, time_diff % 60
    total_time_str = f"{hh:02d}:{mm:02d}:{ss:02d}"

    km_val = round(dist_val / 1000.0, 2)
    fare_val = round(km_val * DONG_GIA)
    trip_id = f"C4567_{int(start_ts)}"
    
    # Ghi vào DATA_4567
    row_data = [
        get_next_stt("DATA_4567"), trip_id, start_time_str, end_time_str, total_time_str,                 
        st.session_state.cust_name, st.session_state.cust_phone,                         
        fare_val, st.session_state['user_name'], DONG_GIA, km_val, fare_val, "HOÀN THÀNH CUỐC XE"            
    ]
    append_row_to_sheet("DATA_4567", row_data)
    
    # Xóa khỏi CACHE_4567
    delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)
    update_driver_status(st.session_state["user_phone"], "Trực tuyến")
    
    # Dọn dẹp URL để app không bị kẹt ở trạng thái stop
    for p in ["action", "dist", "start", "cname", "cphone"]:
        if p in st.query_params: del st.query_params[p]
    
    st.rerun()

# ============================================================
# 6. GIAO DIỆN CHÍNH
# ============================================================
st.markdown(f"<h3 style='text-align:center; color:#00A86B; margin:0;'>🛵 4567 XE ÔM</h3>", unsafe_allow_html=True)
st.markdown(f"<div style='text-align:center; font-size:16px; margin-bottom:10px;'>Tài xế: <b>{st.session_state['user_name']}</b> | <span style='color:green;'>🟢 Sẵn sàng</span></div>", unsafe_allow_html=True)

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
    st.markdown(
        """<div class="marquee-container"><marquee behavior="scroll" direction="left" scrollamount="4">📢 Hướng dẫn: Nhập thông tin bên dưới rồi bấm BẮT ĐẦU CHẠY. Kính chúc bác tài thượng lộ bình an!</marquee></div>""",
        unsafe_allow_html=True
    )
    
    st.markdown("<h4 style='text-align:center; color:#1e293b; margin-top:0;'>📍 NHẬP THÔNG TIN KHÁCH</h4>", unsafe_allow_html=True)
    cust_name_in = st.text_input("TÊN KHÁCH HÀNG:", placeholder="Bỏ trống nếu là khách vãng lai")
    cust_phone_in = st.text_input("SĐT KHÁCH HÀNG:", placeholder="SĐT khách hàng...")

    if st.button("🟢 BẮT ĐẦU CHẠY", type="primary", use_container_width=True):
        reset_trip()
        st.session_state.trip_active = True
        st.session_state.trip_started_at = time.time()
        st.session_state.cust_name = cust_name_in.strip() if cust_name_in.strip() else "Khách vãng lai"
        st.session_state.cust_phone = cust_phone_in.strip()
        st.session_state.trip_id = f"C4567_{int(st.session_state.trip_started_at)}"
        
        # Ghi tạm vào CACHE_4567
        cache_row = [
            get_next_stt("CACHE_4567"), st.session_state.trip_id, get_vn_time(st.session_state.trip_started_at), "---", "---",                              
            st.session_state.cust_name, st.session_state.cust_phone, 0, st.session_state['user_name'], DONG_GIA, 0, 0, "BẮT ĐẦU CUỐC"                      
        ]
        append_row_to_sheet("CACHE_4567", cache_row)
        update_driver_status(st.session_state["user_phone"], "Đang chạy xe")
        st.rerun()

# ---> TRẠNG THÁI 2: ĐANG CHẠY (HTML thu gọn, không lẹm viền, nút to rõ)
elif st.session_state.trip_active:
    current_start_ts = st.session_state.get('trip_started_at', time.time())
    
    html_live_tracker = f"""
    <style>
        body {{ margin: 0; padding: 0; overflow: hidden; background: white; }}
        .btn-stop {{ width: 100%; background: #ef4444; color: white; border: none; border-radius: 12px; padding: 18px; font-size: 22px; font-weight: 900; cursor: pointer; }}
    </style>
    <div style="text-align: center;">
        <div style="color: #64748b; font-size: 15px; font-weight: bold;">CƯỚC PHÍ TẠM TÍNH</div>
        <div id="price" style="color: #059669; font-size: 48px; font-weight: 900; margin: 5px 0;">0 đ</div>
        <div style="color: #334155; font-size: 18px; font-weight: bold; margin-bottom: 20px;"><span id="km" style="color:#0284c7; font-size:22px;">0.00</span> km &nbsp;•&nbsp; {DONG_GIA:,.0f} đ/km</div>
        
        <button id="btnStop" class="btn-stop" onclick="stopTripNow()">🛑 KẾT THÚC CHUYẾN</button>
        <div id="debug_acc" style="font-size: 12px; color: #64748b; margin-top: 10px;">Đang định vị GPS...</div>
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
                document.getElementById("debug_acc").innerText = "GPS đã sẵn sàng";
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
        btn.innerText = "⏳ ĐANG CHỐT ĐƠN..."; btn.style.background = "#64748b"; btn.disabled = true;
        
        let finalDist = localStorage.getItem("xeom_total_meters") || "0";
        localStorage.removeItem("xeom_total_meters");
        
        let parentUrl;
        try {{ parentUrl = new URL(window.parent.location.href); }} catch(e) {{ parentUrl = new URL(window.location.href); }}
        
        parentUrl.searchParams.set("action", "stop");
        parentUrl.searchParams.set("dist", finalDist);
        parentUrl.searchParams.set("start", "{current_start_ts}");
        parentUrl.searchParams.set("cname", "{st.session_state.get('cust_name', 'Khách vãng lai')}");
        parentUrl.searchParams.set("cphone", "{st.session_state.get('cust_phone', '')}");
        parentUrl.searchParams.set("phone", "{st.session_state.get('user_phone', '')}"); 
        
        try {{ window.top.location.href = parentUrl.toString(); }} catch(e) {{ window.location.href = parentUrl.toString(); }}
    }}
    </script>
    """
    components.html(html_live_tracker, height=260)

# ---> TRẠNG THÁI 3: KẾT THÚC (Hiện Bill ngay lập tức)
elif not st.session_state.trip_active and st.session_state.trip_ended_at:
    km = st.session_state.trip_total_m / 1000.0
    fare = round(km * DONG_GIA)
    
    st.markdown(
        f"""
        <div class="receipt-box">
            <div style="font-size: 22px; font-weight: 900; color: #0f172a;">HÓA ĐƠN CHUYẾN ĐI</div>
            <hr style="border: 1px dashed #94a3b8; margin: 10px 0;">
            <div style="text-align: left; font-size:16px; line-height:1.8; color: #334155;">
                <b>Khách hàng:</b> {st.session_state.get('cust_name', 'Khách vãng lai')}<br>
                <b>Quãng đường:</b> {km:.2f} km<br>
                <b>Đơn giá:</b> {DONG_GIA:,.0f} đ/km<br>
            </div>
            <div style="font-size:32px; font-weight:900; color:#059669; text-align:center; margin-top:10px;">
                {fare:,.0f} VNĐ
            </div>
            <div style="margin-top:10px; font-size:14px; font-style:italic; color:#64748b;">Dữ liệu đã được lưu thành công!</div>
        </div>
        """, unsafe_allow_html=True
    )
    st.write("")
    if st.button("♻️ NHẬN CUỐC XE MỚI", type="primary", use_container_width=True):
        reset_trip()
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# 7. KHU VỰC HỖ TRỢ & ĐĂNG XUẤT (NẰM GỌN GÀNG BÊN DƯỚI)
# ============================================================
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
        km_val = round(st.session_state.trip_total_m / 1000.0, 2)
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
