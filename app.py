import math
import time
import urllib.parse
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="4567 Xe Ôm — Google Sheets Edition", page_icon="🛵", layout="centered"
)

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
        try:
            sheet = client.open_by_key(SHEET_KEY)
        except Exception:
            sheet = client.open("4567_XEOM_2026")
        ws = sheet.worksheet(tab_name)
        return ws, ws.get_all_records()
    except Exception as e:
        st.error(f"Lỗi kết nối Google Sheets ({tab_name}): {e}")
        return None, []

def append_row_to_sheet(tab_name, row_values):
    try:
        client = init_google_sheet_client()
        try:
            sheet = client.open_by_key(SHEET_KEY)
        except Exception:
            sheet = client.open("4567_XEOM_2026")
        ws = sheet.worksheet(tab_name)
        ws.append_row(row_values)
        return True
    except Exception as e:
        st.error(f"Lỗi ghi dữ liệu vào {tab_name}: {e}")
        return False

# ============================================================
# CSS GIAO DIỆN XANH SM
# ============================================================
st.markdown(
    """
    <style>
    .stApp { background-color: #f8fafc; }
    .block-container { max-width: 720px; padding-top: 1.2rem; padding-bottom: 2.5rem; padding-left: 1rem; padding-right: 1rem; }
    .app-header {
        background: linear-gradient(135deg, #00A86B 0%, #00804D 100%);
        padding: 20px 24px; border-radius: 20px; color: white; margin-bottom: 16px;
        box-shadow: 0 8px 24px rgba(0, 168, 107, 0.24);
    }
    .app-title { font-size: 22px; font-weight: 900; margin: 0; color: white; }
    .app-subtitle { margin: 4px 0 0 0; color: #e2e8f0; font-size: 13px; font-weight: 500; }
    .status-badge { display: inline-block; padding: 5px 12px; border-radius: 999px; font-size: 11px; font-weight: 700; background: rgba(255, 255, 255, 0.2); color: #ffffff; margin-top: 8px; }
    .section-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 20px; margin-bottom: 14px; box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04); }
    .section-title { font-size: 15px; font-weight: 800; color: #0f172a; margin-bottom: 4px; text-transform: uppercase; }
    .section-desc { font-size: 13px; color: #64748b; margin-bottom: 14px; line-height: 1.4; }
    div.stButton > button {
        border-radius: 12px !important; font-weight: 800 !important; min-height: 50px !important;
        background-color: #00A86B !important; color: white !important; border: none !important;
        box-shadow: 0 4px 12px rgba(0, 168, 107, 0.2);
    }
    div.stButton > button:hover { background-color: #008f5a !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# KHỞI TẠO SESSION STATE & TỰ ĐỘNG ĐĂNG NHẬP
# ============================================================
defaults = {
    "logged_in": False,
    "user_phone": "",
    "user_name": "",
    "customer_info": "",
    "trip_active": False,
    "trip_id": "",
    "trip_started_at": None,
    "trip_ended_at": None,
    "trip_total_m": 0.0,
    "trip_status": "Chưa bắt đầu",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

DONG_GIA = 5000  # VNĐ / km
GPS_ACCURACY_MAX_M = 60
MIN_MOVE_M = 4

# Ghi nhớ đăng nhập từ query params
if not st.session_state["logged_in"] and "phone" in st.query_params:
    saved_phone = st.query_params["phone"]
    if saved_phone:
        _, login_records = get_worksheet_data("DANG_NHAP")
        matched_user = None
        if saved_phone.upper() == "KHÁCH HÀNG":
            matched_user = {"SĐT": "KHÁCH HÀNG", "TÊN TÀI XẾ": "Khách hàng tự do"}
        else:
            for row in login_records:
                if str(row.get("SĐT", "")).strip() == str(saved_phone).strip():
                    matched_user = row
                    break
        if matched_user:
            st.session_state["logged_in"] = True
            st.session_state["user_phone"] = str(matched_user.get("SĐT", ""))
            st.session_state["user_name"] = str(matched_user.get("TÊN TÀI XẾ", "Thành viên"))

# ============================================================
# MÀN HÌNH ĐĂNG NHẬP
# ============================================================
if not st.session_state["logged_in"]:
    st.markdown(
        """
        <div class="app-header">
            <div class="app-title">🛵 4567 XE ÔM</div>
            <div class="app-subtitle">Hệ thống quản lý trực tuyến qua Google Sheets</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">🔐 Đăng nhập hệ thống</div>
            <div class="section-desc">Nhập số điện thoại tài xế được cấp phép trong danh sách trang tính để tiếp tục.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    phone_input = st.text_input("Số điện thoại tài xế / Khách hàng:", placeholder="Ví dụ: 0978666620 hoặc KHÁCH HÀNG")
    remember_me = st.checkbox("Ghi nhớ đăng nhập (Không cần đăng nhập lại lần sau)", value=True)
    
    if st.button("XÁC NHẬN ĐĂNG NHẬP", use_container_width=True):
        if phone_input.strip() == "":
            st.warning("Ní ơi, vui lòng nhập số điện thoại hoặc tên tài khoản!")
        else:
            with st.spinner("Đang kiểm tra dữ liệu từ Trang tính..."):
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
                    if remember_me:
                        st.query_params["phone"] = st.session_state["user_phone"]
                    else:
                        if "phone" in st.query_params:
                            del st.query_params["phone"]
                    st.success(f"Xin chào **{st.session_state['user_name']}**! Đăng nhập thành công.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Số điện thoại không tồn tại trong danh sách phân quyền (`DANG_NHAP`)!")
    st.stop()

# ============================================================
# XỬ LÝ SỰ KIỆN KẾT THÚC CHUYẾN TỨC THÌ QUA URL PARAMS
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

    cust_info = st.query_params.get("cust", st.session_state.get("customer_info", "Khách vãng lai"))
    st.session_state.customer_info = cust_info

    st.session_state.trip_active = False
    st.session_state.trip_ended_at = time.time()
    st.session_state.trip_total_m = dist_val
    st.session_state.trip_status = "Đã hoàn thành"
    
    start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_ts))
    end_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.session_state['trip_ended_at']))
    km_val = round(dist_val / 1000.0, 2)
    fare_val = round(km_val * DONG_GIA)
    trip_id = f"C4567_{int(start_ts)}"
    
    row_data = [
        trip_id, 
        start_time_str,
        end_time_str,
        st.session_state['user_phone'],
        st.session_state['user_name'],
        cust_info,
        km_val,
        DONG_GIA,
        fare_val,
        "HOÀN THÀNH CUỐC XE"
    ]
    
    # 4. & 5. GHI ĐỒNG THỜI VÀO CACHE_4567 VÀ DATA_4567 KHI KẾT THÚC
    append_row_to_sheet("CACHE_4567", row_data)
    append_row_to_sheet("DATA_4567", row_data)
    
    # Giữ lại trạng thái đăng nhập
    phone_val = st.query_params.get("phone", "")
    st.query_params.clear()
    if phone_val:
        st.query_params["phone"] = phone_val
        
    st.rerun()

# ============================================================
# GIAO DIỆN CHÍNH
# ============================================================
col_logo, col_text = st.columns([1, 4], vertical_alignment="center")
with col_logo:
    st.write("🛵 **4567**")
with col_text:
    st.markdown(
        f"""
        <div class="app-header" style="margin-bottom:0; padding: 12px 18px;">
            <div style="font-size: 16px; font-weight: 800;">Tài xế: {st.session_state['user_name']}</div>
            <div class="status-badge">● SĐT: {st.session_state['user_phone']} | Online Sheets</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")

def reset_trip():
    st.session_state.trip_active = False
    st.session_state.trip_started_at = None
    st.session_state.trip_ended_at = None
    st.session_state.trip_total_m = 0.0
    st.session_state.trip_status = "Chưa bắt đầu"

# ============================================================
# TRẠNG THÁI 1: SẴN SÀNG NHẬN KHÁCH
# ============================================================
if not st.session_state.trip_active and not st.session_state.trip_ended_at:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">🚦 Sẵn sàng nhận khách</div>
            <div class="section-desc">Nhập thông tin khách hàng (nếu có) và bấm bắt đầu để kích hoạt định vị GPS thời gian thực.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cust_input = st.text_input("Thông tin khách hàng (SĐT / Tên / Ghi chú):", placeholder="Ví dụ: Anh Nam - 0912345678 (Có thể bỏ trống)")

    if st.button("🟢 BẮT ĐẦU CUỐC XE", use_container_width=True):
        reset_trip()
        st.session_state.trip_active = True
        st.session_state.trip_started_at = time.time()
        st.session_state.customer_info = cust_input.strip() if cust_input.strip() else "Khách vãng lai"
        st.session_state.trip_id = f"C4567_{int(st.session_state.trip_started_at)}"
        
        start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.session_state.trip_started_at))
        
        # 3. GHI NGAY THỜI GIAN THỰC & THÔNG TIN BẮT ĐẦU VÀO CACHE_4567 TRÊN TRANG TÍNH
        cache_row = [
            st.session_state.trip_id,
            start_time_str,
            "Đang di chuyển...",
            st.session_state['user_phone'],
            st.session_state['user_name'],
            st.session_state.customer_info,
            0,
            DONG_GIA,
            0,
            "BẮT ĐẦU CUỐC"
        ]
        append_row_to_sheet("CACHE_4567", cache_row)
        st.rerun()

# ============================================================
# TRẠNG THÁI 2: HÀNH TRÌNH ĐANG DIỄN RA
# ============================================================
elif st.session_state.trip_active:
    st.markdown(
        f"""
        <div class="section-card" style="border-color: #00A86B;">
            <div class="section-title" style="color: #00A86B;">🟢 Hành trình đang diễn ra</div>
            <div class="section-desc" style="margin-bottom:0;">Khách hàng: <b>{st.session_state.get('customer_info', 'Khách vãng lai')}</b><br>Dữ liệu được Cache thời gian thực. Bấm Kết thúc bên dưới để chốt cuốc.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    current_start_ts = st.session_state.get('trip_started_at', time.time())
    cust_param = urllib.parse.quote(st.session_state.get('customer_info', 'Khách vãng lai'))

    # 1. & 2. SỬA LỖI NÚT KẾT THÚC TỨC THÌ (Gỡ bỏ iframe Sandbox + Dùng Top Navigation chuẩn)
    html_live_tracker = f"""
    <div style="font-family: system-ui, -apple-system, sans-serif; padding: 16px; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; text-align: center;">
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 14px; padding: 16px; margin-bottom: 14px;">
            <div style="color: #166534; font-size: 12px; font-weight: 700; text-transform: uppercase;">Cước phí tạm tính</div>
            <div id="price" style="color: #0f172a; font-size: 34px; font-weight: 900; margin: 4px 0;">0 VNĐ</div>
            <div style="color: #475569; font-size: 12px;"><span id="km">0.00</span> km • {DONG_GIA:,.0f} đ/km</div>
        </div>
        
        <button id="btnStop" onclick="stopTripNow()" style="width: 100%; background: #dc2626; color: white; border: none; border-radius: 12px; padding: 16px; font-size: 16px; font-weight: 900; cursor: pointer; box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);">
            💳 KẾT THÚC & GHI VÀO SHEET NGAY
        </button>
        <div id="debug_acc" style="font-size: 11px; color: #94a3b8; margin-top: 10px;">GPS: Đang theo dõi & Cache Active...</div>
    </div>

    <script>
    localStorage.setItem("xeom_trip_active", "true");
    localStorage.setItem("xeom_start_time", "{current_start_ts}");

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
    let totalMeters = parseFloat(localStorage.getItem("xeom_total_meters") || "0.0");
    const dongGia = {DONG_GIA};

    if (totalMeters > 0) {{
        let km = totalMeters / 1000.0;
        document.getElementById("km").innerText = km.toFixed(2);
        document.getElementById("price").innerText = Math.round(km * dongGia).toLocaleString('vi-VN') + " VNĐ";
    }}

    if ("geolocation" in navigator) {{
        navigator.geolocation.watchPosition(
            function(pos) {{
                let lat = pos.coords.latitude, lon = pos.coords.longitude, acc = pos.coords.accuracy;
                document.getElementById("debug_acc").innerText = "Sai số GPS: ±" + acc.toFixed(1) + " m | Cache OK";
                if (acc > {GPS_ACCURACY_MAX_M}) return;
                if (lastLat === null) {{ lastLat = lat; lastLon = lon; return; }}
                let d = calcCrow(lastLat, lastLon, lat, lon);
                if (d >= {MIN_MOVE_M} && d < 120) {{
                    totalMeters += d;
                    lastLat = lat; lastLon = lon;
                    localStorage.setItem("xeom_total_meters", totalMeters);
                    let km = totalMeters / 1000.0;
                    document.getElementById("km").innerText = km.toFixed(2);
                    document.getElementById("price").innerText = Math.round(km * dongGia).toLocaleString('vi-VN') + " VNĐ";
                }}
            }},
            err => {{ document.getElementById("debug_acc").innerText = "Lỗi GPS: " + err.message; }},
            {{ enableHighAccuracy: true, maximumAge: 0, timeout: 15000 }}
        );
    }}

    function stopTripNow() {{
        let btn = document.getElementById("btnStop");
        btn.innerText = "⏳ ĐANG LƯU DỮ LIỆU...";
        btn.style.background = "#64748b";
        btn.disabled = true;

        let finalDist = localStorage.getItem("xeom_total_meters") || "0";
        localStorage.removeItem("xeom_total_meters");
        localStorage.removeItem("xeom_trip_active");
        localStorage.removeItem("xeom_start_time");
        
        let targetUrl = window.top.location.href.split('?')[0] + "?action=stop&dist=" + finalDist + "&start={current_start_ts}&cust={cust_param}";
        window.top.location.href = targetUrl;
    }}
    </script>
    """
    components.html(html_live_tracker, height=220)

# ============================================================
# TRẠNG THÁI 3: HOÀN THÀNH CUỐC XE & HIỆU ỨNG CELEBRATION
# ============================================================
elif not st.session_state.trip_active and st.session_state.trip_ended_at:
    km = st.session_state.trip_total_m / 1000.0
    fare = km * DONG_GIA

    # 6. HIỆU ỨNG KẾT THÚC (Confetti Bắn Pháo Hoa Trực Tiếp Khung Hình)
    confetti_html = """
    <canvas id="confetti-canvas" style="position:fixed; top:0; left:0; width:100vw; height:100vh; pointer-events:none; z-index:9999;"></canvas>
    <script>
    (function() {
        let canvas = document.getElementById('confetti-canvas');
        let ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        let particles = [];
        let colors = ['#00A86B', '#10B981', '#F59E0B', '#EF4444', '#3B82F6', '#8B5CF6'];
        
        for (let i = 0; i < 80; i++) {
            particles.push({
                x: canvas.width / 2,
                y: canvas.height / 2,
                r: Math.random() * 6 + 4,
                vx: (Math.random() - 0.5) * 12,
                vy: (Math.random() - 0.7) * 12,
                color: colors[Math.floor(Math.random() * colors.length)],
                life: 100
            });
        }
        
        function update() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach((p, index) => {
                p.x += p.vx;
                p.y += p.vy;
                p.vy += 0.2;
                p.life -= 1.5;
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.fillStyle = p.color;
                ctx.globalAlpha = Math.max(0, p.life / 100);
                ctx.fill();
            });
            if (particles.some(p => p.life > 0)) {
                requestAnimationFrame(update);
            }
        }
        update();
    })();
    </script>
    """
    components.html(confetti_html, height=1)

    st.markdown(
        f"""
        <div class="section-card" style="border-color: #00A86B;">
            <div class="section-title" style="color: #00A86B;">🎉 HOÀN THÀNH & ĐÃ GHI VÀO DATA SHEET</div>
            <div class="section-desc">Dữ liệu chuyến xe đã được ghi thành công tức thì vào tab <b>CACHE_4567</b> và <b>DATA_4567</b>!</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("📏 Quãng đường", f"{km:.2f} km")
    with c2: st.metric("💰 Đơn giá", f"{DONG_GIA:,.0f}đ")
    with c3: st.metric("💵 Tổng tiền", f"{fare:,.0f} VNĐ")

    st.info(f"👤 **Khách hàng:** {st.session_state.get('customer_info', 'Khách vãng lai')} | 🛵 **Tài xế:** {st.session_state['user_name']}")
    st.success("✅ Đã cập nhật thành công dữ liệu vào Google Sheets phục vụ theo dõi & xét khen thưởng!")
    
    st.write("")
    if st.button("♻️ BẮT ĐẦU CUỐC MỚI", use_container_width=True):
        reset_trip()
        st.rerun()

# ============================================================
# KHU VỰC XEM BÁO CÁO THỜI GIAN THỰC TỪ GOOGLE SHEETS
# ============================================================
st.markdown("---")
with st.expander("📊 XEM BÁO CÁO THỜI GIAN THỰC (TỪ GOOGLE SHEETS)", expanded=False):
    st.info("Dữ liệu được tải trực tiếp từ Tab `DATA_4567` và `CACHE_4567` trên Trang tính.")
    
    tab_rep1, tab_rep2 = st.tabs(["📦 Dữ liệu DATA_4567", "⚡ Bộ nhớ CACHE_4567"])
    
    with tab_rep1:
        _, data_records = get_worksheet_data("DATA_4567")
        if data_records:
            df_data = pd.DataFrame(data_records)
            st.dataframe(df_data, use_container_width=True)
        else:
            st.warning("Chưa có dữ liệu trong bảng `DATA_4567`.")
            
    with tab_rep2:
        _, cache_records = get_worksheet_data("CACHE_4567")
        if cache_records:
            df_cache = pd.DataFrame(cache_records)
            st.dataframe(df_cache, use_container_width=True)
        else:
            st.warning("Chưa có dữ liệu ghi nhận trong `CACHE_4567`.")

st.write("")
if st.button("🔒 ĐĂNG XUẤT TÀI KHOẢN", type="secondary", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["user_phone"] = ""
    st.session_state["user_name"] = ""
    st.query_params.clear()
    st.rerun()
