import math
import time
import datetime
import urllib.parse
import gspread
import pandas as pd
import pytz
import streamlit as st
import streamlit.components.v1 as components
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="4567 Xe Ôm — Tài Xế (v4.1)", page_icon="🛵", layout="centered"
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
# HÀM TÍNH CƯỚC THEO BIỂU GIÁ BẬC THANG CHUẨN
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
# CSS GIAO DIỆN TỐI ƯU CHO ĐỘ TUỔI 45-67
# ============================================================
st.markdown(
    """
    <style>
    .stApp { background-color: #f8fafc; }
    .block-container { max-width: 600px; padding-top: 1.5rem; padding-bottom: 2rem; padding-left: 1rem; padding-right: 1rem; }
    .driver-header { background: linear-gradient(135deg, #00A86B 0%, #007A4D 100%); padding: 16px 20px; border-radius: 16px; color: white; margin-bottom: 14px; box-shadow: 0 4px 12px rgba(0, 168, 107, 0.2); }
    .driver-name { font-size: 20px; font-weight: 900; margin: 0; color: white; }
    .driver-phone { font-size: 14px; margin-top: 4px; color: #e2e8f0; font-weight: 700; }
    
    div.stButton > button { 
        border-radius: 14px !important; 
        font-weight: 900 !important; 
        font-size: 18px !important; 
        min-height: 58px !important; 
        background-color: #00A86B !important; 
        color: white !important; 
        border: none !important; 
        box-shadow: 0 4px 12px rgba(0, 168, 107, 0.25);
    }
    input { font-size: 18px !important; font-weight: 700 !important; }
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

GPS_ACCURACY_MAX_M = 50
MIN_MOVE_M = 3

# ============================================================
# XỬ LÝ KẾT THÚC CUỐC XE & LƯU TRỮ ĐỒNG BỘ
# ============================================================
if "action" in st.query_params and st.query_params["action"] == "stop":
    try:
        dist_val = float(st.query_params.get("dist", 0.0))
    except (TypeError, ValueError):
        dist_val = 0.0

    try:
        start_ts = float(st.query_params.get("start", time.time()))
    except (TypeError, ValueError):
        start_ts = time.time()

    end_ts = time.time()
    cname = st.query_params.get("cname", "Khách vãng lai")
    cphone = st.query_params.get("cphone", "")
    trip_id = f"C4567_{int(start_ts)}"

    start_time_str = get_vn_time(start_ts)
    end_time_str = get_vn_time(end_ts)
    
    time_diff = max(0, int(end_ts - start_ts))
    hh, mm, ss = time_diff // 3600, (time_diff % 3600) // 60, time_diff % 60
    total_time_str = f"{hh:02d}:{mm:02d}:{ss:02d}"

    km_val = round(dist_val / 1000.0, 2)
    fare_val = calculate_fare(km_val)
    
    stt = get_next_stt("DATA_4567")
    row_data = [
        stt, trip_id, start_time_str, end_time_str, total_time_str,
        cname, cphone, fare_val, st.session_state.get('user_name', 'Tài xế'),
        get_current_unit_price_desc(km_val), km_val, fare_val, "HOÀN THÀNH CUỐC XE"
    ]
    
    append_row_to_sheet("DATA_4567", row_data)
    delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)
    
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()

# ============================================================
# MÀN HÌNH 1: ĐĂNG NHẬP TÀI XẾ
# ============================================================
if not st.session_state["logged_in"]:
    st.markdown(
        """
        <div style="text-align: center; padding: 20px 0 10px 0;">
            <div style="font-size: 42px;">🛵</div>
            <div style="font-size: 24px; font-weight: 900; color: #0f172a; margin-top: 6px;">4567 XE ÔM (v4.1)</div>
            <div style="font-size: 14px; color: #64748b; font-weight: 600;">Hệ thống định vị & tính cước tự động</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
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
    if st.button("🟢 BẮT ĐẦU HÀNH TRÌNH GPS", use_container_width=True):
        st.session_state["trip_active"] = True
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

# ============================================================
# MÀN HÌNH 3: THEO DÕI HÀNH TRÌNH GPS TỰ ĐỘNG (v4.1 FIXED)
# ============================================================
else:
    st.markdown(
        f"""
        <div style="background: #ffffff; border: 2px solid #00A86B; border-radius: 16px; padding: 14px 16px; margin-bottom: 12px;">
            <div style="color: #00A86B; font-size: 14px; font-weight: 800; text-transform: uppercase;">🟢 BƯỚC 2: HÀNH TRÌNH GPS Đang CHẠY</div>
            <div style="font-size: 15px; color: #334155; margin-top: 6px;">Khách: <b>{st.session_state.get('cust_name', 'Khách vãng lai')}</b> | SĐT: <b>{st.session_state.get('cust_phone', '---')}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    current_start_ts = st.session_state.get('trip_started_at', time.time())
    cname_val = st.session_state.get('cust_name', 'Khách vãng lai')
    cphone_val = st.session_state.get('cust_phone', '')
    
    html_live_tracker = f"""
    <div style="font-family: system-ui, -apple-system, sans-serif; padding: 4px; background: #ffffff; border-radius: 16px; text-align: center; position: relative;">
        <!-- Toast Notification Banner -->
        <div id="toast_msg" style="visibility: hidden; background-color: #0f172a; color: #fff; text-align: center; border-radius: 10px; padding: 12px 18px; position: absolute; z-index: 100; left: 50%; transform: translateX(-50%); bottom: 85px; font-size: 14px; font-weight: 700; box-shadow: 0 4px 12px rgba(0,0,0,0.2); transition: opacity 0.3s ease; opacity: 0;">
            Thông báo
        </div>

        <div style="background: #f0fdf4; border: 2px solid #86efac; border-radius: 16px; padding: 16px; margin-bottom: 14px;">
            <div style="color: #166534; font-size: 13px; font-weight: 800; text-transform: uppercase;" id="status_label">HÀNH TRÌNH ĐANG ĐO GPS</div>
            <div id="price" style="color: #0f172a; font-size: 42px; font-weight: 900; margin: 4px 0;">0 VNĐ</div>
            <div style="display: flex; justify-content: space-around; margin-top: 10px; font-size: 14px; font-weight: 800; color: #334155;">
                <div>⏱ Thời gian: <span id="timer">00:00:00</span></div>
                <div>🛣 Quãng đường: <span id="km">0.00</span> km</div>
            </div>
            <div id="rate_desc" style="color: #64748b; font-size: 13px; margin-top: 6px; font-weight: 600;">Đơn giá: Miễn phí dưới 3km</div>
        </div>
        
        <div style="display: flex; gap: 12px; margin-bottom: 10px;">
            <button id="btnPause" onclick="togglePause()" style="flex: 1; background: #d97706; color: white; border: none; border-radius: 14px; padding: 14px; font-size: 16px; font-weight: 900; cursor: pointer; box-shadow: 0 4px 10px rgba(217, 119, 6, 0.3);">
                ⏸ TẠM DỪNG
            </button>
            <a id="btnStop" href="#" onclick="handleStop(event)" target="_top" style="display: flex; justify-content: center; align-items: center; flex: 1; background: #dc2626; color: white; border-radius: 14px; padding: 14px; font-size: 16px; font-weight: 900; text-decoration: none; box-shadow: 0 4px 10px rgba(220, 38, 38, 0.3);">
                🔴 KẾT THÚC CHUYẾN
            </a>
        </div>
        <div id="debug_acc" style="font-size: 12px; color: #64748b; font-weight: 600;">GPS: Đang bắt vệ tinh chính xác...</div>
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

        // Cập nhật sẵn link href để trình duyệt di động nhận diện chuẩn xác hành động native click
        let baseUrl = window.location.href.split('?')[0];
        try {{
            if (window.parent && window.parent.location) {{
                baseUrl = window.parent.location.href.split('?')[0];
            }}
        }} catch(err) {{}}

        let targetUrl = baseUrl + "?action=stop&dist=" + totalMeters + "&start=" + startTimestamp + "&cname=" + encodeURIComponent(customerName) + "&cphone=" + encodeURIComponent(customerPhone);
        document.getElementById("btnStop").href = targetUrl;
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
            label.innerText = "⏸ ĐANG TẠM DỪNG";
            label.style.color = "#d97706";
            showToast("⏸ Đã tạm dừng đo GPS.", "#d97706");
        }} else {{
            btn.innerText = "⏸ TẠM DỪNG";
            btn.style.background = "#d97706";
            label.innerText = "🟢 HÀNH TRÌNH ĐANG ĐO GPS";
            label.style.color = "#166534";
            showToast("▶️ Đã tiếp tục hành trình.", "#00A86B");
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

    function handleStop(e) {{
        vibrate(90);
        localStorage.removeItem("xeom_v4_meters");
        localStorage.removeItem("xeom_v4_seconds");
        // Link sẽ tự động mở target="_top" theo thuộc tính href đã được update liên tục!
    }}
    </script>
    """
    components.html(html_live_tracker, height=350)
