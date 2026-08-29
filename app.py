import datetime
import math
import time
import gspread
import pytz
import streamlit as st
import streamlit.components.v1 as components
from google.oauth2.service_account import Credentials

# Cấu hình trang - Ẩn Sidebar, tập trung toàn màn hình
st.set_page_config(
    page_title="4567 Xe Ôm — Pro Edition", page_icon="🛵", layout="centered", initial_sidebar_state="collapsed"
)

# ============================================================
# COMPONENT GPS ĐỘC LẬP (KHÔNG DÙNG URL, KHÔNG POP-UP)
# ============================================================
gps_tracker_html = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { margin: 0; padding: 0; font-family: sans-serif; text-align: center; background: transparent; }
        .price { color: #059669; font-size: 50px; font-weight: 900; margin: 5px 0; }
        .btn { width: 100%; background: #ef4444; color: white; border: none; border-radius: 12px; padding: 18px; font-size: 22px; font-weight: 900; cursor: pointer; box-shadow: 0 4px 10px rgba(239, 68, 68, 0.3); }
    </style>
    <script>
        function sendMessageToStreamlitClient(type, data) {
            var outData = Object.assign({isStreamlitMessage: true, type: type}, data);
            window.parent.postMessage(outData, "*");
        }
        function init() { sendMessageToStreamlitClient("streamlit:componentReady", {apiVersion: 1}); }
        function setFrameHeight(height) { sendMessageToStreamlitClient("streamlit:setFrameHeight", {height: height}); }
        function sendDataValue(value) { sendMessageToStreamlitClient("streamlit:setComponentValue", {value: value}); }

        let totalMeters = parseFloat(localStorage.getItem("xeom_total_meters") || "0.0");
        let dongGia = 5000;
        
        window.addEventListener("message", function(event) {
            if (event.data.type === "streamlit:render") {
                setFrameHeight(250);
                if (event.data.args && event.data.args.dongGia) {
                    dongGia = event.data.args.dongGia;
                    updateDisplay();
                }
            }
        });

        let lastLat = null, lastLon = null;
        function calcCrow(lat1, lon1, lat2, lon2) {
            var R = 6371000;
            var dLat = (lat2 - lat1) * Math.PI / 180;
            var dLon = (lon2 - lon1) * Math.PI / 180;
            var a = Math.sin(dLat/2) * Math.sin(dLat/2) + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLon/2) * Math.sin(dLon/2);
            return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        }

        function updateDisplay() {
            let km = totalMeters / 1000.0;
            document.getElementById("km").innerText = km.toFixed(2);
            document.getElementById("price").innerText = Math.round(km * dongGia).toLocaleString('vi-VN') + " đ";
        }

        if ("geolocation" in navigator) {
            navigator.geolocation.watchPosition(
                function(pos) {
                    let lat = pos.coords.latitude, lon = pos.coords.longitude, acc = pos.coords.accuracy;
                    document.getElementById("debug_acc").innerText = "GPS OK (Sai số: ±" + acc.toFixed(1) + " m)";
                    if (acc > 60) return;
                    if (lastLat === null) { lastLat = lat; lastLon = lon; return; }
                    let d = calcCrow(lastLat, lastLon, lat, lon);
                    if (d >= 4 && d < 150) {
                        totalMeters += d;
                        lastLat = lat; lastLon = lon;
                        localStorage.setItem("xeom_total_meters", totalMeters);
                        updateDisplay();
                    }
                },
                err => { document.getElementById("debug_acc").innerText = "Lỗi GPS: " + err.message; },
                { enableHighAccuracy: true, maximumAge: 0, timeout: 10000 }
            );
        }

        function stopTrip() {
            let btn = document.getElementById("btnStop");
            btn.innerText = "⏳ ĐANG LƯU DỮ LIỆU..."; btn.style.background = "#64748b"; btn.disabled = true;
            let finalDist = totalMeters;
            localStorage.removeItem("xeom_total_meters");
            // Bắn tín hiệu ngầm về Python, triệt tiêu mọi loại Pop-up hay giật trang
            sendDataValue(finalDist);
        }
    </script>
</head>
<body onload="init(); updateDisplay();">
    <div style="color: #64748b; font-size: 14px; font-weight: bold;">CƯỚC PHÍ TẠM TÍNH</div>
    <div id="price" class="price">0 đ</div>
    <div style="color: #334155; font-size: 18px; font-weight: bold; margin-bottom: 20px;"><span id="km" style="color:#0284c7; font-size:22px;">0.00</span> km</div>
    <button id="btnStop" class="btn" onclick="stopTrip()">🛑 KẾT THÚC CHUYẾN</button>
    <div id="debug_acc" style="font-size: 12px; color: #94a3b8; margin-top: 10px;">Đang dò GPS...</div>
</body>
</html>
"""
gps_tracker = components.declare_component("gps_tracker", html=gps_tracker_html)


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
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(dict(st.secrets["connections"]["gsheets"]), scopes=scope)
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
        if not ws: return False
        safe_row = [str(x) if x is not None else "" for x in row_values]
        
        # BƯỚC VÁ LỖI CỰC MẠNH: Dùng insert_data_option='INSERT_ROWS'
        # Ép Google Sheets chèn thẳng 1 hàng mới ngay dưới dữ liệu hiện tại,
        # dẹp bỏ hoàn toàn bệnh trôi tuốt xuống dòng 1000.
        ws.append_row(safe_row, value_input_option='USER_ENTERED', insert_data_option='INSERT_ROWS')
        return True
    except Exception as e:
        print(f"Lỗi ghi sheet {tab_name}: {e}") 
        return False

def delete_row_from_sheet(tab_name, col_name, value):
    try:
        ws, records = get_worksheet_data(tab_name)
        if not ws or not records: return False
        headers = ws.row_values(1)
        if col_name not in headers: return False
        
        for i in range(len(records), 0, -1):
            if str(records[i-1].get(col_name, "")).strip() == str(value).strip():
                ws.delete_rows(i + 1)
                return True
        return False
    except Exception as e:
        print(f"Lỗi xóa dòng ở sheet {tab_name}: {e}")
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
# 2. CSS GIAO DIỆN (ĐƠN GIẢN, VỪA 1 MÀN HÌNH, KHÔNG POP-UP)
# ============================================================
st.markdown(
    """
    <style>
    [data-testid="stHeader"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    footer { display: none !important; }
    
    .stApp { background-color: #ffffff; }
    .block-container { max-width: 500px; padding: 1rem !important; }
    
    div.stButton > button { 
        border-radius: 12px !important; 
        font-weight: 900 !important; 
        font-size: 22px !important; 
        min-height: 60px !important; 
    }
    
    .action-box { padding: 10px; margin-bottom: 10px; }
    .btn-sos { background: #ef4444; color: white; padding: 14px; border-radius: 12px; text-align: center; font-weight: bold; font-size: 16px; text-decoration: none; display: block; }
    .btn-zalo { background: #0068ff; color: white; padding: 14px; border-radius: 12px; text-align: center; font-weight: bold; font-size: 16px; text-decoration: none; display: block; }
    </style>
    """, unsafe_allow_html=True
)

# ============================================================
# 3. QUẢN LÝ TRẠNG THÁI
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

# Tự động đăng nhập
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
    st.markdown("<h2 style='text-align:center; color:#00A86B; font-weight:900;'>🛵 4567 XE ÔM</h2>", unsafe_allow_html=True)
    phone_input = st.text_input("Nhập Số điện thoại của bạn:")
    
    if st.button("🚀 VÀO CA LÀM VIỆC", type="primary", use_container_width=True):
        if phone_input.strip() == "":
            st.warning("Vui lòng nhập số điện thoại!")
        else:
            with st.spinner("Đang kết nối hệ thống..."):
                _, login_records = get_worksheet_data("DANG_NHAP")
                matched_user = None
                
                if phone_input.upper() == "KHÁCH HÀNG":
                    matched_user = {"SĐT": "KHÁCH HÀNG", "TÊN TÀI XẾ": "Khách tự do"}
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
    st.stop()


# ============================================================
# 5. GIAO DIỆN CHÍNH (XỬ LÝ MỌI THỨ TẠI 1 TRANG)
# ============================================================
st.markdown(f"<h3 style='text-align:center; color:#00A86B; margin:0;'>🛵 4567 XE ÔM</h3>", unsafe_allow_html=True)
st.markdown(f"<div style='text-align:center; font-size:16px; margin-bottom:10px; color:#475569;'>Tài xế: <b>{st.session_state['user_name']}</b></div>", unsafe_allow_html=True)

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
    cust_name_in = st.text_input("Tên khách hàng:", placeholder="Để trống nếu là khách vãng lai")
    cust_phone_in = st.text_input("Số điện thoại khách (nếu có):")

    if st.button("🟢 BẮT ĐẦU CHẠY", type="primary", use_container_width=True):
        reset_trip()
        st.session_state.trip_active = True
        st.session_state.trip_started_at = time.time()
        st.session_state.cust_name = cust_name_in.strip() if cust_name_in.strip() else "Khách vãng lai"
        st.session_state.cust_phone = cust_phone_in.strip()
        st.session_state.trip_id = f"C4567_{int(st.session_state.trip_started_at)}"
        
        # Ghi Nháp vào CACHE
        cache_row = [
            get_next_stt("CACHE_4567"), st.session_state.trip_id, get_vn_time(st.session_state.trip_started_at), "---", "---",                              
            st.session_state.cust_name, st.session_state.cust_phone, 0, st.session_state['user_name'], DONG_GIA, 0, 0, "ĐANG CHẠY"                      
        ]
        append_row_to_sheet("CACHE_4567", cache_row)
        update_driver_status(st.session_state["user_phone"], "Đang chạy xe")
        st.rerun()

# ---> TRẠNG THÁI 2: ĐANG CHẠY
elif st.session_state.trip_active:
    current_start_ts = st.session_state.get('trip_started_at', time.time())
    current_trip_id = st.session_state.get('trip_id', f"C4567_{int(current_start_ts)}")
    
    # Kích hoạt UI đếm quãng đường. Bấm KẾT THÚC, JS bắn số mét thẳng về đây!
    returned_distance = gps_tracker(dongGia=DONG_GIA, key=f"tracker_{current_trip_id}")
    
    if returned_distance is not None:
        # Nhận dữ liệu ngầm và tính toán ngay lập tức
        dist_val = float(returned_distance)
        st.session_state.trip_ended_at = time.time()
        st.session_state.trip_total_m = dist_val
        st.session_state.trip_active = False
        
        start_time_str = get_vn_time(current_start_ts)
        end_time_str = get_vn_time(st.session_state.trip_ended_at)
        time_diff = max(0, int(st.session_state.trip_ended_at - current_start_ts))
        hh, mm, ss = time_diff // 3600, (time_diff % 3600) // 60, time_diff % 60
        total_time_str = f"{hh:02d}:{mm:02d}:{ss:02d}"

        km_val = round(dist_val / 1000.0, 2)
        fare_val = round(km_val * DONG_GIA)
        
        # Ghi chính thức vào DATA_4567
        row_data = [
            int(get_next_stt("DATA_4567")), current_trip_id, start_time_str, end_time_str, total_time_str,                 
            st.session_state.get("cust_name", ""), st.session_state.get("cust_phone", ""), int(fare_val),                         
            str(st.session_state.get('user_name', '')), int(DONG_GIA), float(km_val), int(fare_val), "HOÀN THÀNH"            
        ]
        
        # Lưu thực tế và Xóa Cache (Chạy êm ru bên dưới Python)
        append_row_to_sheet("DATA_4567", row_data)
        delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", current_trip_id)
        update_driver_status(st.session_state.get("user_phone", ""), "Trực tuyến")
        
        st.rerun()

# ---> TRẠNG THÁI 3: KẾT THÚC (GIAO DIỆN PHẲNG, KHÔNG BOX, KHÔNG POP-UP)
elif not st.session_state.trip_active and st.session_state.trip_ended_at:
    km = st.session_state.trip_total_m / 1000.0
    fare = round(km * DONG_GIA)
    
    st.markdown(
        f"""
        <div style="text-align:center; padding: 10px 0;">
            <div style="color:#059669; font-size:26px; font-weight:900;">✅ ĐÃ XONG CUỐC XE</div>
            <div style="font-size:15px; color:#475569; margin-top:5px;">Hệ thống đã lưu báo cáo.</div>
            
            <div style="margin-top: 25px; text-align: left; padding: 0 10px; color: #1e293b;">
                <p style="font-size:18px; margin: 8px 0;">👤 Khách: <b>{st.session_state.get('cust_name', 'Khách vãng lai')}</b></p>
                <p style="font-size:18px; margin: 8px 0;">📏 Quãng đường: <b>{km:.2f} km</b></p>
                <p style="font-size:18px; margin: 8px 0;">🏷 Đơn giá: <b>{DONG_GIA:,.0f} đ/km</b></p>
            </div>
            
            <div style="font-size:45px; font-weight:900; color:#059669; margin: 25px 0;">
                {fare:,.0f} đ
            </div>
        </div>
        """, unsafe_allow_html=True
    )
    
    if st.button("♻️ NHẬN KHÁCH MỚI", type="primary", use_container_width=True):
        reset_trip()
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# 6. KHU VỰC HỖ TRỢ VÀ ĐĂNG XUẤT
# ============================================================
c_sos, c_zalo = st.columns(2)
with c_sos:
    st.markdown('<a href="tel:0978666620" class="btn-sos">🚨 GỌI SOS</a>', unsafe_allow_html=True)
with c_zalo:
    st.markdown('<a href="https://zalo.me/0978666620" class="btn-zalo" target="_blank">💬 ZALO ADMIN</a>', unsafe_allow_html=True)

st.write("")
if st.button("🔒 ĐĂNG XUẤT", use_container_width=True):
    if st.session_state.get("trip_active", False): 
        end_ts = time.time()
        start_ts = st.session_state.get("trip_started_at", end_ts)
        trip_id = st.session_state.get("trip_id", f"C4567_{int(start_ts)}")
        km_val = round(st.session_state.get("trip_total_m", 0.0) / 1000.0, 2)
        fare_val = round(km_val * DONG_GIA)
        
        row_data = [
            int(get_next_stt("DATA_4567")), str(trip_id), str(get_vn_time(start_ts)), str(get_vn_time(end_ts)), "00:00:00",
            str(st.session_state.get("cust_name", "")), str(st.session_state.get("cust_phone", "")), int(fare_val),
            str(st.session_state.get("user_name", "")), int(DONG_GIA), float(km_val), int(fare_val), "ÉP KẾT THÚC KHI ĐĂNG XUẤT"
        ]
        append_row_to_sheet("DATA_4567", row_data)
        delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)

    update_driver_status(st.session_state.get("user_phone", ""), "Ngoại tuyến")
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()
