import math
import time
import datetime
import gspread
import pandas as pd
import pytz
import streamlit as st
import streamlit.components.v1 as components
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="4567 Xe Ôm — Tài Xế (v4.3 Pro)", page_icon="🛵", layout="centered"
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
# KHỞI TẠO SESSION STATE QUẢN LÝ 3 CỬA SỔ
# ============================================================
if "step" not in st.session_state:
    st.session_state["step"] = 1  # 1: Đăng nhập, 2: Nhận khách/GPS, 3: Bill chi tiết

defaults = {
    "user_phone": "",
    "user_name": "",
    "cust_name": "",
    "cust_phone": "",
    "trip_id": "",
    "trip_started_at": None,
    "final_dist": 0.0,
    "final_end_ts": None
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

GPS_ACCURACY_MAX_M = 50
MIN_MOVE_M = 3

# ============================================================
# BẮT TÍN HIỆU THANH TOÁN TỪ JAVASCRIPT ĐỂ CHUYỂN SANG CỬA SỔ 3
# ============================================================
if "action" in st.query_params and st.query_params["action"] == "stop":
    try:
        st.session_state["final_dist"] = float(st.query_params.get("dist", 0.0))
    except (TypeError, ValueError):
        st.session_state["final_dist"] = 0.0

    try:
        start_ts = float(st.query_params.get("start", time.time()))
    except (TypeError, ValueError):
        start_ts = time.time()

    st.session_state["trip_started_at"] = start_ts
    st.session_state["final_end_ts"] = time.time()
    st.session_state["cust_name"] = st.query_params.get("cname", "Khách vãng lai")
    st.session_state["cust_phone"] = st.query_params.get("cphone", "")
    st.session_state["trip_id"] = f"C4567_{int(start_ts)}"

    # Xóa query params trên URL để tránh lặp lại khi load lại trang
    st.query_params.clear()
    st.session_state["step"] = 3
    st.rerun()

# ============================================================
# CỬA SỔ 1: MÀN HÌNH ĐĂNG NHẬP TÀI XẾ
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
                    st.session_state["step"] = 2  # Chuyển sang cửa sổ 2
                    st.success(f"Chào bác **{st.session_state['user_name']}**! Đang vào ứng dụng...")
                    time.sleep(0.4)
                    st.rerun()
                else:
                    st.error("❌ Số điện thoại không đúng hoặc chưa được cấp quyền!")
    st.stop()

# ============================================================
# HEADER CHUNG CHO CỬA SỔ 2 VÀ 3
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
# CỬA SỔ 2: MÀN HÌNH NHẬP KHÁCH & ĐO GPS HÀNH TRÌNH
# ============================================================
if st.session_state["step"] == 2:
    # Nếu chưa bắt đầu chuyến -> Hiển thị form nhập thông tin khách
    if not st.session_state.get("trip_active_state", False):
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
    
    # Đang trong chuyến -> Hiển thị đồng hồ GPS thời gian thực
    else:
        st.markdown(
            f"""
            <div class="pro-card" style="border-left: 5px solid #059669; background: #f8fafc;">
                <div style="color: #059669; font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;">🟢 ĐANG ĐO HÀNH TRÌNH GPS</div>
                <div style="font-size: 14px; color: #1e293b; margin-top: 4px; font-weight: 700;">Khách: {st.session_state.get('cust_name', 'Khách vãng lai')} &bull; SĐT: {st.session_state.get('cust_phone', '---')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        current_start_ts = st.session_state.get('trip_started_at', time.time())
        cname_val = st.session_state.get('cust_name', 'Khách vãng lai')
        cphone_val = st.session_state.get('cust_phone', '')
        
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

            <!-- Toast Notification -->
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
                <div id="rate_desc" style="color: #a7f3d0; font-size: 12px; margin-top: 8px; font-weight: 600;">Đơn giá: Miễn phí dưới 3km</div>
            </div>
            
            <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                <button id="btnPause" class="action-btn" onclick="togglePause()" style="flex: 1; background: #d97706; color: white; box-shadow: 0 6px 16px rgba(217, 119, 6, 0.3);">
                    ⏸ TẠM DỪNG
                </button>
                <button id="btnPay" class="action-btn" onclick="handlePayment(event)" style="flex: 1.2; background: #059669; color: white; font-size: 15px; box-shadow: 0 6px 16px rgba(5, 150, 105, 0.3);">
                    💵 THANH TOÁN
                </button>
            </div>
            <div id="debug_acc" style="text-align: center; font-size: 11px; color: #64748b; font-weight: 600;">GPS: Đang bắt tín hiệu vệ tinh...</div>
        </div>

        <script>
        let isPaused = false;
        let secondsElapsed = parseInt(localStorage.getItem("xeom_v4_seconds") || "0");
        let totalMeters = parseFloat(localStorage.getItem("xeom_v4_meters") || "0.0");
        let startTimestamp = {current_start_ts};
        let customerName = "{cname_val}";
        let customerPhone = "{cphone_val}";

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
            if (km < 3.0) return 0;
            if (km < 11.0) return Math.round(km * 4500);
            if (km < 40.0) return Math.round(km * 4000);
            return Math.round(km * 5500);
        }}

        function getRateDescJS(km) {{
            if (km < 3.0) return "0 đ/km (Miễn phí < 3km)";
            if (km < 11.0) return "4,500 đ/km (3km - dưới 11km)";
            if (km < 40.0) return "4,000 đ/km (11km - dưới 40km)";
            return "5,500 đ/km (Từ 40km trở lên)";
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

        updateUI();

        setInterval(function() {{
            if (!isPaused) {{
                secondsElapsed++;
                localStorage.setItem("xeom_v4_seconds", secondsElapsed);
                updateUI();
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
                showToast("⏸ Đã tạm dừng đo GPS.", "#d97706");
            }} else {{
                btn.innerText = "⏸ TẠM DỪNG";
                btn.style.background = "#d97706";
                label.innerText = "🟢 ĐỒNG HỒ TÍNH CƯỚC THỜI GIAN THỰC";
                label.style.color = "#34d399";
                showToast("▶️ Tiếp tục hành trình.", "#059669");
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
                    
                    if (acc > {GPS_ACCURACY_MAX_M}) return;
                    if (lastLat === null) {{ lastLat = lat; lastLon = lon; return; }}
                    
                    if (!isPaused) {{
                        let d = calcCrow(lastLat, lastLon, lat, lon);
                        if (d >= {MIN_MOVE_M} && d < 120) {{
                            totalMeters += d;
                            localStorage.setItem("xeom_v4_meters", totalMeters);
                            updateUI();
                        }}
                    }}
                    lastLat = lat; lastLon = lon;
                }},
                err => {{ document.getElementById("debug_acc").innerText = "Lỗi GPS: Vui lòng bật định vị điện thoại!"; }},
                {{ enableHighAccuracy: true, maximumAge: 0, timeout: 15000 }}
            );
        }}

        function handlePayment(e) {{
            vibrate(90);
            localStorage.removeItem("xeom_v4_meters");
            localStorage.removeItem("xeom_v4_seconds");

            let baseUrl = window.location.href.split('?')[0];
            try {{
                if (window.parent && window.parent.location) {{
                    baseUrl = window.parent.location.href.split('?')[0];
                }}
            }} catch(err) {{}}

            let targetUrl = baseUrl + "?action=stop&dist=" + totalMeters + "&start=" + startTimestamp + "&cname=" + encodeURIComponent(customerName) + "&cphone=" + encodeURIComponent(customerPhone);
            
            showToast("Đang xử lý thanh toán...", "#059669");
            window.open(targetUrl, '_self');
        }}
        </script>
        """
        components.html(html_live_tracker, height=310)

# ============================================================
# CỬA SỔ 3: MÀN HÌNH HÓA ĐƠN CHI TIẾT RIÊNG BIỆT
# ============================================================
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
    
    # Lưu vào Google Sheets và xóa cache (chỉ chạy 1 lần khi vào step 3)
    if not st.session_state.get("saved_to_sheet", False):
        stt = get_next_stt("DATA_4567")
        row_data = [
            stt, trip_id, start_time_str, end_time_str, total_time_str,
            cname, cphone, fare_val, driver_name_val,
            unit_desc, km_val, fare_val, "ĐÃ THANH TOÁN"
        ]
        append_row_to_sheet("DATA_4567", row_data)
        delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)
        st.session_state["saved_to_sheet"] = True

    # Nút bấm quay lại màn hình chính trực tiếp bằng Streamlit (hoàn toàn mượt mà)
    if st.button("⬅️ QUAY LẠI MÀN HÌNH CHÍNH", use_container_width=True):
        st.session_state["trip_active_state"] = False
        st.session_state["saved_to_sheet"] = False
        st.session_state["step"] = 2  # Quay lại cửa sổ nhận khách
        st.rerun()

    # Hiển thị hóa đơn chi tiết gọn gàng bên dưới
    invoice_html = f"""
    <div style="font-family: system-ui, -apple-system, sans-serif; padding: 2px;">
        <div style="background: #ffffff; border-radius: 20px; padding: 18px 20px; border: 2px solid #059669; box-shadow: 0 10px 25px rgba(0,0,0,0.05); margin-bottom: 12px;">
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
    </div>
    """
    components.html(invoice_html, height=520)
