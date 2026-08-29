import datetime
import math
import time
import urllib.parse
import gspread
import pandas as pd
import pytz
import streamlit as st
import streamlit.components.v1 as components
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="4567 Xe Ôm — Google Sheets Edition", page_icon="🛵", layout="centered"
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
        try:
            sheet = client.open_by_key(SHEET_KEY)
        except Exception:
            sheet = client.open("4567_XEOM_2026")
        ws = sheet.worksheet(tab_name)
        return ws, ws.get_all_records()
    except Exception as e:
        st.error(f"Lỗi kết nối Google Sheets ({tab_name}): {e}")
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
        st.error(f"Lỗi xóa dữ liệu khỏi {tab_name}: {e}")
        return False

# ============================================================
# CSS GIAO DIỆN CAO CẤP (PHONG CÁCH APP GỌI XE HIỆN ĐẠI)
# ============================================================
st.markdown(
    """
    <style>
    .stApp { background-color: #ffffff; }
    .block-container { max-width: 480px; padding-top: 1.5rem; padding-bottom: 3rem; padding-left: 1.2rem; padding-right: 1.2rem; }
    
    /* Header kiểu app gọi xe */
    .auth-hero { text-align: center; padding: 20px 0 10px 0; }
    .auth-title { font-size: 26px; font-weight: 900; color: #00A86B; line-height: 1.3; margin-bottom: 8px; }
    .auth-subtitle { font-size: 14px; color: #64748b; line-height: 1.5; padding: 0 10px; margin-bottom: 24px; }
    
    /* Vòng tròn trang trí minh họa mờ */
    .hero-circle-box {
        width: 180px; height: 180px; background: linear-gradient(135deg, rgba(0,168,107,0.08) 0%, rgba(0,128,77,0.02) 100%);
        border-radius: 50%; margin: 0 auto 20px auto; display: flex; align-items: center; justify-content: center;
        border: 2px dashed rgba(0,168,107,0.2); font-size: 54px; box-shadow: 0 10px 30px rgba(0,168,107,0.06);
    }

    /* Khung nhập số điện thoại tùy biến */
    .phone-input-card {
        background: #ffffff; border: 1px solid #cbd5e1; border-radius: 16px; padding: 4px 16px;
        display: flex; align-items: center; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    
    /* Tùy chỉnh nút bấm chung */
    div.stButton > button { border-radius: 14px !important; font-weight: 800 !important; min-height: 52px !important; background-color: #00A86B !important; color: white !important; border: none !important; box-shadow: 0 6px 16px rgba(0, 168, 107, 0.25); font-size: 15px !important; }
    div.stButton > button:hover { background-color: #008f5a !important; }
    
    /* Dashboard & Thẻ thông tin khi đã đăng nhập */
    .app-header { background: linear-gradient(135deg, #00A86B 0%, #00804D 100%); padding: 20px 24px; border-radius: 20px; color: white; margin-bottom: 16px; box-shadow: 0 8px 24px rgba(0, 168, 107, 0.24); }
    .status-badge { display: inline-block; padding: 5px 12px; border-radius: 999px; font-size: 11px; font-weight: 700; background: rgba(255, 255, 255, 0.2); color: #ffffff; margin-top: 8px; margin-right: 4px; }
    .section-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 20px; margin-bottom: 14px; box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04); }
    .section-title { font-size: 15px; font-weight: 800; color: #0f172a; margin-bottom: 4px; text-transform: uppercase; }
    .section-desc { font-size: 13px; color: #64748b; margin-bottom: 14px; line-height: 1.4; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# KHỞI TẠO SESSION STATE
# ============================================================
defaults = {
    "logged_in": False,
    "user_phone": "",
    "user_name": "",
    "cust_name": "",
    "cust_phone": "",
    "trip_active": False,
    "trip_id": "",
    "trip_started_at": None,
    "trip_ended_at": None,
    "trip_total_m": 0.0,
    "trip_status": "Chưa bắt đầu",
    "show_balloons": False
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

DONG_GIA = 5000
GPS_ACCURACY_MAX_M = 60
MIN_MOVE_M = 4

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
# MÀN HÌNH ĐĂNG NHẬP (LỘT XÁC GIAO DIỆN MỚI)
# ============================================================
if not st.session_state["logged_in"]:
    # Thanh chọn ngôn ngữ giả lập ở góc phải trên
    col_top_l, col_top_r = st.columns([3, 2])
    with col_top_r:
        st.markdown(
            """
            <div style="text-align: right; font-size: 13px; font-weight: 600; color: #475569; padding-bottom: 10px;">
                🇻🇳 Việt Nam | VI ▾
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        """
        <div class="auth-hero">
            <div class="hero-circle-box">🛵</div>
            <div class="auth-title">4567 Xe Ôm — Mọi thứ trong tầm tay</div>
            <div class="auth-subtitle">Đăng nhập bằng số điện thoại tài xế để bắt đầu hành trình xanh của bạn</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Khung nhập liệu tinh chỉnh gọn gàng
    c_flag, c_input = st.columns([1.2, 3.8])
    with c_flag:
        st.markdown(
            """
            <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 14px; padding: 11px 12px; text-align: center; font-weight: 700; font-size: 14px; color: #334155; margin-bottom: 16px;">
                🇻🇳 +84
            </div>
            """,
            unsafe_allow_html=True
        )
    with c_input:
        phone_input = st.text_input("SĐT", placeholder="Nhập số điện thoại", label_visibility="collapsed")

    remember_me = st.checkbox("Ghi nhớ đăng nhập phiên làm việc", value=True)
    
    st.write("")
    if st.button("TIẾP TỤC", use_container_width=True):
        if not phone_input or phone_input.strip() == "":
            st.warning("Ní ơi, vui lòng nhập số điện thoại hoặc tên tài khoản!")
        else:
            with st.spinner("Đang xác thực tài khoản..."):
                _, login_records = get_worksheet_data("DANG_NHAP")
                matched_user = None
                if phone_input.strip().upper() == "KHÁCH HÀNG":
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
                    st.success(f"Xin chào **{st.session_state['user_name']}**! Đang chuyển hướng...")
                    time.sleep(0.8)
                    st.rerun()
                else:
                    st.error("❌ Số điện thoại không tồn tại trong danh sách phân quyền (`DANG_NHAP`)!")

    # Phần phân cách phía dưới
    st.markdown(
        """
        <div style="text-align: center; margin-top: 30px; border-top: 1px solid #f1f5f9; padding-top: 20px;">
            <span style="font-size: 12px; color: #94a3b8; background: #ffffff; padding: 0 10px;">Hoặc hỗ trợ qua hệ thống</span>
        </div>
        <div style="text-align: center; margin-top: 15px; font-size: 13px; font-weight: 700; color: #00A86B;">
            📞 Hotline / Zalo: 0978.666.620
        </div>
        """,
        unsafe_allow_html=True
    )
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

    cname = st.query_params.get("cname", st.session_state.get("cust_name", "Khách vãng lai"))
    cphone = st.query_params.get("cphone", st.session_state.get("cust_phone", ""))
    
    st.session_state.cust_name = cname
    st.session_state.cust_phone = cphone

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
        stt,                            
        trip_id,                        
        start_time_str,                 
        end_time_str,                   
        total_time_str,                 
        cname,                          
        cphone,                         
        fare_val,                       
        st.session_state['user_name'],  
        DONG_GIA,                       
        km_val,                         
        fare_val,                       
        "HOÀN THÀNH CUỐC XE"            
    ]
    
    append_row_to_sheet("DATA_4567", row_data)
    delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)
    
    st.session_state["show_balloons"] = True
    
    phone_val = st.query_params.get("phone", "")
    st.query_params.clear()
    if phone_val:
        st.query_params["phone"] = phone_val
        
    st.rerun()

# ============================================================
# GIAO DIỆN CHÍNH (SAU KHI ĐĂNG NHẬP)
# ============================================================
col_logo, col_text = st.columns([1, 4], vertical_alignment="center")
with col_logo:
    st.write("🛵 **4567**")
with col_text:
    st.markdown(
        f"""
        <div class="app-header" style="margin-bottom:0; padding: 12px 18px;">
            <div style="font-size: 16px; font-weight: 800;">Tài xế: {st.session_state['user_name']}</div>
            <div class="status-badge">● SĐT: {st.session_state['user_phone']}</div>
            <div class="status-badge" style="background: rgba(255, 255, 255, 0.3);">📞 Hotline/Zalo: 0978666620</div>
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
    st.session_state.show_balloons = False

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

    c1, c2 = st.columns(2)
    with c1:
        cust_name_in = st.text_input("Tên khách hàng:", placeholder="VD: Anh Nam")
    with c2:
        cust_phone_in = st.text_input("SĐT khách (nếu có):", placeholder="VD: 0912345678")

    if st.button("🟢 BẮT ĐẦU CUỐC XE", use_container_width=True):
        reset_trip()
        st.session_state.trip_active = True
        st.session_state.trip_started_at = time.time()
        
        st.session_state.cust_name = cust_name_in.strip() if cust_name_in.strip() else "Khách vãng lai"
        st.session_state.cust_phone = cust_phone_in.strip()
        st.session_state.trip_id = f"C4567_{int(st.session_state.trip_started_at)}"
        
        start_time_str = get_vn_time(st.session_state.trip_started_at)
        
        stt_cache = get_next_stt("CACHE_4567")
        cache_row = [
            stt_cache,                          
            st.session_state.trip_id,           
            start_time_str,                     
            "---",                              
            "---",                              
            st.session_state.cust_name,         
            st.session_state.cust_phone,        
            0,                                  
            st.session_state['user_name'],      
            DONG_GIA,                           
            0,                                  
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
            <div class="section-desc" style="margin-bottom:0;">Khách: <b>{st.session_state.get('cust_name', 'Khách vãng lai')}</b> | SĐT: <b>{st.session_state.get('cust_phone', '---')}</b><br>Đang đồng bộ Cache thời gian thực.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    current_start_ts = st.session_state.get('trip_started_at', time.time())
    
    html_live_tracker = f"""
    <div style="font-family: system-ui, -apple-system, sans-serif; padding: 16px; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; text-align: center;">
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 14px; padding: 16px; margin-bottom: 14px;">
            <div style="color: #166534; font-size: 12px; font-weight: 700; text-transform: uppercase;">Cước phí tạm tính</div>
            <div id="price" style="color: #0f172a; font-size: 34px; font-weight: 900; margin: 4px 0;">0 VNĐ</div>
            <div style="color: #475569; font-size: 12px;"><span id="km">0.00</span> km • {DONG_GIA:,.0f} đ/km</div>
        </div>
        
        <button id="btnStop" onclick="stopTripNow()" style="width: 100%; background: #dc2626; color: white; border: none; border-radius: 14px; padding: 16px; font-size: 16px; font-weight: 900; cursor: pointer; box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);">
            💳 KẾT THÚC CHUYẾN XE & ĐẨY QUA DATA
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
        btn.innerText = "⏳ ĐANG XỬ LÝ DỮ LIỆU...";
        btn.style.background = "#64748b";
        btn.disabled = true;

        let finalDist = localStorage.getItem("xeom_total_meters") || "0";
        localStorage.removeItem("xeom_total_meters");
        localStorage.removeItem("xeom_trip_active");
        localStorage.removeItem("xeom_start_time");
        
        let baseUrl = window.location.href.split('?')[0];
        try {{ if (window.parent && window.parent.location) {{ baseUrl = window.parent.location.href.split('?')[0]; }} }} catch(e) {{}}
        
        let targetUrl = baseUrl + "?action=stop&dist=" + finalDist + "&start={current_start_ts}";
        try {{ window.top.location.href = targetUrl; }} catch(e) {{ window.location.href = targetUrl; }}
    }}
    </script>
    """
    components.html(html_live_tracker, height=200)

# ============================================================
# TRẠNG THÁI 3: HOÀN THÀNH CUỐC XE
# ============================================================
elif not st.session_state.trip_active and st.session_state.trip_ended_at:
    
    if st.session_state.get("show_balloons", False):
        st.balloons()
        st.session_state["show_balloons"] = False

    km = st.session_state.trip_total_m / 1000.0
    fare = km * DONG_GIA

    st.markdown(
        f"""
        <div class="section-card" style="border-color: #00A86B;">
            <div class="section-title" style="color: #00A86B;">🎉 KẾT QUẢ CUỐC XE HOÀN TẤT</div>
            <div class="section-desc">Hệ thống đã tự động đẩy dữ liệu sang tab <b>DATA_4567</b> và dọn dẹp bộ nhớ đệm thành công!</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("📏 Quãng đường", f"{km:.2f} km")
    with c2: st.metric("💰 Đơn giá", f"{DONG_GIA:,.0f}đ")
    with c3: st.metric("💵 Tổng tiền", f"{fare:,.0f} VNĐ")

    st.info(f"👤 **Khách hàng:** {st.session_state.get('cust_name', 'Khách vãng lai')} | 🛵 **Tài xế:** {st.session_state['user_name']}")
    
    st.write("")
    if st.button("♻️ SẴN SÀNG NHẬN CHUYẾN MỚI", use_container_width=True):
        reset_trip()
        st.rerun()

# ============================================================
# KHU VỰC XEM BÁO CÁO
# ============================================================
st.markdown("---")
with st.expander("📊 XEM BÁO CÁO THỜI GIAN THỰC (TỪ GOOGLE SHEETS)", expanded=False):
    tab_rep1, tab_rep2 = st.tabs(["📦 Dữ liệu DATA_4567", "⚡ Bộ nhớ CACHE_4567"])
    
    with tab_rep1:
        _, data_records = get_worksheet_data("DATA_4567")
        if data_records:
            st.dataframe(pd.DataFrame(data_records), use_container_width=True, hide_index=True)
        else:
            st.warning("Chưa có dữ liệu trong bảng `DATA_4567`.")
            
    with tab_rep2:
        _, cache_records = get_worksheet_data("CACHE_4567")
        if cache_records:
            st.dataframe(pd.DataFrame(cache_records), use_container_width=True, hide_index=True)
        else:
            st.success("Hiện CACHE đang trống (đã được dọn dẹp).")

# ============================================================
# ĐĂNG XUẤT TÀI KHOẢN & LƯU DATA DỰ PHÒNG
# ============================================================
st.write("")
if st.button("🔒 ĐĂNG XUẤT TÀI KHOẢN", type="secondary", use_container_width=True):
    if st.session_state.trip_active:
        end_ts = time.time()
        start_ts = st.session_state.trip_started_at
        trip_id = st.session_state.trip_id
        start_time_str = get_vn_time(start_ts)
        end_time_str = get_vn_time(end_ts)
        
        time_diff = max(0, int(end_ts - start_ts))
        hh, mm, ss = time_diff // 3600, (time_diff % 3600) // 60, time_diff % 60
        total_time_str = f"{hh:02d}:{mm:02d}:{ss:02d}"

        km_val = round(st.session_state.trip_total_m / 1000.0, 2)
        fare_val = round(km_val * DONG_GIA)
        
        stt = get_next_stt("DATA_4567")
        row_data = [
            stt,
            trip_id,
            start_time_str,
            end_time_str,
            total_time_str,
            st.session_state.get("cust_name", "Khách vãng lai"),
            st.session_state.get("cust_phone", ""),
            fare_val,
            st.session_state['user_name'],
            DONG_GIA,
            km_val,
            fare_val,
            "ÉP KẾT THÚC BẰNG ĐĂNG XUẤT"
        ]
        append_row_to_sheet("DATA_4567", row_data)
        delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)

    st.session_state["logged_in"] = False
    st.session_state["user_phone"] = ""
    st.session_state["user_name"] = ""
    st.session_state["trip_active"] = False
    st.query_params.clear()
    st.rerun()
