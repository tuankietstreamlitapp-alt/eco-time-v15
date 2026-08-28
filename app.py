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
SHEET_TITLE = "4567_XEOM_2026"

@st.cache_resource
def init_google_sheet_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Lấy thông tin xác thực từ Streamlit Secrets
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client

def get_worksheet_data(tab_name):
    try:
        client = init_google_sheet_client()
        sheet = client.open(SHEET_TITLE)
        ws = sheet.worksheet(tab_name)
        return ws, ws.get_all_records()
    except Exception as e:
        st.error(f"Lỗi kết nối Google Sheets ({tab_name}): {e}")
        return None, []

def append_row_to_sheet(tab_name, row_values):
    try:
        client = init_google_sheet_client()
        sheet = client.open(SHEET_TITLE)
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
# KHỞI TẠO SESSION STATE & ĐĂNG NHẬP (TAB DANG_NHAP)
# ============================================================
defaults = {
    "logged_in": False,
    "user_phone": "",
    "user_name": "",
    "trip_active": False,
    "trip_started_at": None,
    "trip_ended_at": None,
    "trip_total_m": 0.0,
    "trip_status": "Chưa bắt đầu",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Giao diện Đăng nhập nếu chưa xác thực
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
    if st.button("XÁC NHẬN ĐĂNG NHẬP", use_container_width=True):
        if phone_input.strip() == "":
            st.warning("Ní ơi, vui lòng nhập số điện thoại hoặc tên tài khoản!")
        else:
            with st.spinner("Đang kiểm tra dữ liệu từ Trang tính..."):
                _, login_records = get_worksheet_data("DANG_NHAP") #[span_4](start_span)[span_4](end_span)
                
                # Kiểm tra khớp dữ liệu trong tab DANG_NHAP[span_5](start_span)[span_5](end_span)
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
                    st.success(f"Xin chào **{st.session_state['user_name']}**! Đăng nhập thành công.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Số điện thoại không tồn tại trong danh sách phân quyền (`DANG_NHAP`)[span_6](start_span)[span_6](end_span)!")
    st.stop()

# ============================================================
# GIAO DIỆN CHÍNH SAU KHI ĐĂNG NHẬP
# ============================================================
DONG_GIA = 5000  # VNĐ / km
HOTLINE = "0978666620"
GPS_ACCURACY_MAX_M = 60
MIN_MOVE_M = 4

# Header chính
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

# Xử lý kết thúc chuyến từ JS trả về query params
if "action" in st.query_params and st.query_params["action"] == "stop":
    try:
        dist_val = float(st.query_params.get("dist", 0.0))
    except (TypeError, ValueError):
        dist_val = 0.0

    st.session_state.trip_active = False
    st.session_state.trip_ended_at = time.time()
    st.session_state.trip_total_m = dist_val
    st.session_state.trip_status = "Đã hoàn thành"
    
    # Tự động lưu Cache vào Google Sheets (Tab CACHE_4567)[span_7](start_span)[span_7](end_span)
    start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.session_state.get('trip_started_at', time.time())))
    end_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(st.session_state['trip_ended_at']))
    km_val = round(dist_val / 1000.0, 2)
    fare_val = round(km_val * DONG_GIA)
    
    cache_row = [
        "", # STT (để trống hoặc tự tăng)
        start_time_str,
        end_time_str,
        st.session_state['user_name'],
        st.session_state['user_phone'],
        fare_val,
        st.session_state['user_name'],
        km_val,
        fare_val,
        "Hoàn thành chuyến tự động qua GPS"
    ]
    append_row_to_sheet("CACHE_4567", cache_row) #[span_8](start_span)[span_8](end_span)
    
    st.query_params.clear()
    st.rerun()

def reset_trip():
    st.session_state.trip_active = False
    st.session_state.trip_started_at = None
    st.session_state.trip_ended_at = None
    st.session_state.trip_total_m = 0.0
    st.session_state.trip_status = "Chưa bắt đầu"

def start_trip():
    reset_trip()
    st.session_state.trip_active = True
    st.session_state.trip_started_at = time.time()
    st.session_state.trip_status = "Đang chạy"

# ============================================================
# CÁC TRẠNG THÁI CUỐC XE
# ============================================================
# Trạng thái 1: Chưa bắt đầu
if not st.session_state.trip_active and not st.session_state.trip_ended_at:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">🚦 Sẵn sàng nhận khách</div>
            <div class="section-desc">Hệ thống GPS sẵn sàng kích hoạt và đồng bộ dữ liệu trực tiếp lên Trang tính.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🟢 BẮT ĐẦU CUỐC XE", use_container_width=True):
        start_trip()
        st.rerun()

# Trạng thái 2: Đang chạy Real-time
elif st.session_state.trip_active:
    st.markdown(
        """
        <div class="section-card" style="border-color: #00A86B;">
            <div class="section-title" style="color: #00A86B;">🟢 Hành trình đang diễn ra</div>
            <div class="section-desc" style="margin-bottom:0;">Đang đo lường GPS thực tế và khóa sáng màn hình chống ngắt quãng.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    html_live_tracker = f"""
    <div style="font-family: sans-serif; padding: 16px; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; text-align: center;">
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 14px; padding: 16px; margin-bottom: 14px;">
            <div style="color: #166534; font-size: 12px; font-weight: 700; text-transform: uppercase;">Cước phí tạm tính</div>
            <div id="price" style="color: #0f172a; font-size: 34px; font-weight: 900; margin: 4px 0;">0 VNĐ</div>
            <div style="color: #475569; font-size: 12px;"><span id="km">0.00</span> km • {DONG_GIA:,.0f} đ/km</div>
        </div>
        <button onclick="stopTrip()" style="width: 100%; background: #0f172a; color: white; border: none; border-radius: 12px; padding: 14px; font-size: 15px; font-weight: 800; cursor: pointer;">
            💳 KẾT THÚC & LƯU CACHE VÀO SHEET
        </button>
        <div id="debug_acc" style="font-size: 11px; color: #94a3b8; margin-top: 8px;">GPS: Đang kết nối...</div>
    </div>

    <script>
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
                document.getElementById("debug_acc").innerText = "Sai số GPS: ±" + acc.toFixed(1) + " m";
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

    function stopTrip() {{
        localStorage.removeItem("xeom_total_meters");
        let parentUrl = document.referrer ? document.referrer.split('?')[0] : window.location.href.split('?')[0];
        let targetUrl = parentUrl + "?action=stop&dist=" + totalMeters;
        let a = document.createElement("a");
        a.href = targetUrl; a.target = "_top";
        document.body.appendChild(a); a.click();
    }}
    </script>
    """
    components.html(html_live_tracker, height=200)

# Trạng thái 3: Hoàn thành chuyến & Báo cáo Real-time
elif not st.session_state.trip_active and st.session_state.trip_ended_at:
    km = st.session_state.trip_total_m / 1000.0
    fare = km * DONG_GIA

    # Pháo hoa ăn mừng
    components.html(
        """
        <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.browser.min.js"></script>
        <script>setTimeout(() => { confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 } }); }, 200);</script>
        """,
        height=1,
    )

    st.markdown(
        """
        <div class="section-card" style="border-color: #00A86B;">
            <div class="section-title" style="color: #00A86B;">🎉 HOÀN THÀNH VÀ ĐÃ LƯU CACHE</div>
            <div class="section-desc">Dữ liệu chuyến xe đã được ghi thành công vào Google Sheets (`CACHE_4567`)[span_9](start_span)[span_9](end_span)!</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("📏 Quãng đường", f"{km:.2f} km")
    with c2: st.metric("💰 Đơn giá", f"{DONG_GIA:,.0f}đ")
    with c3: st.metric("💵 Tổng tiền", f"{fare:,.0f} VNĐ")

    st.success("✅ Đã đồng bộ dữ liệu lên mây thành công!")
    
    st.write("")
    if st.button("♻️ BẮT ĐẦU CUỐC MỚI", use_container_width=True):
        reset_trip()
        st.rerun()

# ============================================================
# KHU VỰC XEM BÁO CÁO THỜI GIAN THỰC TỪ GOOGLE SHEETS
# ============================================================
st.markdown("---")
with st.expander("📊 XEM BÁO CÁO THỜI GIAN THỰC (TỪ GOOGLE SHEETS)", expanded=False):
    st.info("Dữ liệu được tải trực tiếp từ Tab `DATA_4567` và `CACHE_4567` trên trang tính của ní[span_10](start_span)[span_10](end_span).")
    
    tab_rep1, tab_rep2 = st.tabs(["📦 Dữ liệu DATA_4567", "⚡ Bộ nhớ CACHE_4567"])
    
    with tab_rep1:
        _, data_records = get_worksheet_data("DATA_4567")[span_11](start_span)[span_11](end_span)
        if data_records:
            df_data = pd.DataFrame(data_records)
            st.dataframe(df_data, use_container_width=True)
        else:
            st.warning("Chưa có dữ liệu trong bảng `DATA_4567`[span_12](start_span)[span_12](end_span).")
            
    with tab_rep2:
        _, cache_records = get_worksheet_data("CACHE_4567")[span_13](start_span)[span_13](end_span)
        if cache_records:
            df_cache = pd.DataFrame(cache_records)
            st.dataframe(df_cache, use_container_width=True)
            # Thống kê nhanh tổng doanh thu từ Cache
            if "THÀNH TIỀN" in df_cache.columns:
                total_rev = pd.to_numeric(df_cache["THÀNH TIỀN"], errors='coerce').sum()
                st.metric("Tổng doanh thu lưu trong Cache", f"{total_rev:,.0f} VNĐ")
        else:
            st.warning("Chưa có dữ liệu ghi nhận trong `CACHE_4567`[span_14](start_span)[span_14](end_span).")

# Đăng xuất
st.write("")
if st.button("🔒 ĐĂNG XUẤT TÀI KHOẢN", type="secondary", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["user_phone"] = ""
    st.session_state["user_name"] = ""
    st.rerun()
