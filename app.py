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
    """Ghi 1 dòng vào Google Sheet và trả về (thành công, lỗi)."""
    try:
        client = init_google_sheet_client()
        sheet = client.open_by_key(SHEET_KEY)
        ws = sheet.worksheet(tab_name)
        ws.append_row(row_values, value_input_option="USER_ENTERED")
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"

def save_trip_to_data_sheet(row_values):
    """Ghi DATA_4567 với retry ngắn để giảm lỗi mạng nhất thời."""
    last_error = ""
    for attempt in range(3):
        ok, err = append_row_to_sheet("DATA_4567", row_values)
        if ok:
            return True, ""
        last_error = err
        if attempt < 2:
            time.sleep(1.0)
    return False, last_error

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
# 2. CSS GIAO DIỆN — XANH / SẠCH / ĐẸP / DỄ THAO TÁC
# ============================================================
st.markdown("""
<style>
#MainMenu, footer, header { visibility:hidden !important; }
[data-testid="stHeader"], [data-testid="stDecoration"],
[data-testid="stToolbar"], [data-testid="stStatusWidget"] { display:none !important; }
.stApp { background:#f3faf6; }
.block-container { max-width:600px; padding:.25rem .75rem 1.2rem !important; }
.marquee-container { background:#087f4f; color:#fff; padding:7px 10px; border-radius:9px; font-weight:700; font-size:13px; margin:0 0 11px; overflow:hidden; }
div[data-testid="stTextInput"] label, div[data-testid="stCheckbox"] label { font-size:16px !important; font-weight:700 !important; }
div[data-testid="stTextInput"] input { min-height:46px !important; border-radius:10px !important; font-size:17px !important; }
div.stButton > button { border-radius:11px !important; font-weight:900 !important; font-size:19px !important; min-height:58px !important; box-shadow:none !important; }
.fare-panel { background:#effaf4; border:2px solid #b9e6cd; border-radius:15px; padding:13px 10px 14px; margin-bottom:12px; }
.receipt-box { border:1px solid #cfe4d8; border-radius:14px; padding:17px; text-align:center; background:#fff; margin-bottom:12px; box-shadow:0 3px 12px rgba(10,80,50,.05); }
.support-title { color:#5b7167; text-align:center; font-size:13px; font-weight:800; margin:5px 0 7px; }
.btn-sos,.btn-zalo { color:#fff; padding:11px; border-radius:10px; text-align:center; font-weight:900; font-size:16px; text-decoration:none; display:block; }
.btn-sos { background:#dc2626; } .btn-zalo { background:#0068ff; }
.btn-sos:hover,.btn-zalo:hover { color:#fff; opacity:.92; }
@media(max-width:600px){.block-container{padding-left:.55rem !important;padding-right:.55rem !important;}}
@media print{body *{visibility:hidden}.receipt-print-area,.receipt-print-area *{visibility:visible}.receipt-print-area{position:absolute;left:0;top:0;width:100%}.stButton,.btn-sos,.btn-zalo{display:none !important}}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 3. QUẢN LÝ TRẠNG THÁI
# ============================================================
defaults = {
    "logged_in": False, "user_phone": "", "user_name": "",
    "cust_name": "", "cust_phone": "",
    "trip_active": False, "trip_id": "", "trip_started_at": None, "trip_ended_at": None,
    "trip_total_m": 0.0, "trip_status": "Chưa bắt đầu",
    "login_success_effect": False, "end_trip_effect": False, "data_save_error": ""
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

DONG_GIA = 5000
GPS_ACCURACY_MAX_M = 60
MIN_MOVE_M = 4

# Auto Login
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
# Không dùng div mở/đóng bằng 2 lệnh st.markdown riêng biệt:
# Streamlit sẽ render chúng thành một thanh rỗng độc lập.
if not st.session_state["logged_in"]:
    st.markdown("<h1 style='text-align:center; color:#00A86B; font-size:40px;'>🛵 4567 XE ÔM</h1>", unsafe_allow_html=True)
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
    st.stop()

# ============================================================
# 5. XỬ LÝ KẾT THÚC CHUYẾN TỪ URL
# ============================================================
if "action" in st.query_params and st.query_params["action"] == "stop":
    dist_val = float(st.query_params.get("dist", 0.0))
    start_ts = float(st.query_params.get("start", time.time()))
    
    st.session_state.trip_active = False
    st.session_state.trip_ended_at = time.time()
    st.session_state.trip_total_m = dist_val
    st.session_state.trip_status = "Đã hoàn thành"
    
    cname = st.query_params.get("cname", "Khách vãng lai")
    cphone = st.query_params.get("cphone", "")
    st.session_state.cust_name = cname.replace("%20", " ")
    st.session_state.cust_phone = cphone
    
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
        st.session_state.cust_name, st.session_state.cust_phone,                         
        fare_val, st.session_state['user_name'], DONG_GIA, km_val, fare_val, "HOÀN THÀNH CUỐC XE"            
    ]
    
    append_row_to_sheet("DATA_4567", row_data)
    delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)
    update_driver_status(st.session_state["user_phone"], "Trực tuyến")
    
    st.session_state["end_trip_effect"] = True
    
    if "action" in st.query_params: del st.query_params["action"]
    if "dist" in st.query_params: del st.query_params["dist"]
    if "start" in st.query_params: del st.query_params["start"]
    if "cname" in st.query_params: del st.query_params["cname"]
    if "cphone" in st.query_params: del st.query_params["cphone"]
    
    st.rerun()

if st.session_state.get("login_success_effect"):
    st.toast("Đăng nhập thành công!", icon="✅")
    st.balloons()
    st.session_state["login_success_effect"] = False

if st.session_state.get("data_save_error"):
    st.error(
        "❌ CHƯA LƯU ĐƯỢC CUỘC XE VÀO DATA_4567. "
        "Dữ liệu vẫn được giữ trong CACHE_4567 để tránh mất doanh thu.\n\n"
        f"Chi tiết lỗi Google Sheets: {st.session_state['data_save_error']}"
    )

# ============================================================
# 6. GIAO DIỆN CHÍNH & BANNER CHỮ CHẠY
# ============================================================
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;background:#fff;border:1px solid #d8ebe1;border-radius:13px;padding:9px 12px;margin-bottom:8px;box-shadow:0 3px 10px rgba(10,80,50,.05);">
<div style="font-size:20px;font-weight:900;color:#087f4f;">🛵 4567 XE ÔM</div>
<div style="text-align:right;font-size:13px;line-height:1.25;"><b>{st.session_state['user_name']}</b><br><span style="color:#087f4f;font-weight:900;">● SẴN SÀNG</span></div>
</div>""", unsafe_allow_html=True)

def reset_trip():
    st.session_state.trip_active = False
    st.session_state.trip_started_at = None
    st.session_state.trip_ended_at = None
    st.session_state.trip_total_m = 0.0
    st.session_state.cust_name = ""
    st.session_state.cust_phone = ""


# ---> TRẠNG THÁI 1: CHỜ KHÁCH
if not st.session_state.trip_active and not st.session_state.trip_ended_at:
    # Banner chữ chạy đặt gọn gàng trên cùng của khung
    st.markdown(
        """
        <div class="marquee-container">
            <marquee behavior="scroll" direction="left" scrollamount="5">
                📢 LƯU Ý: Luôn tuân thủ an toàn giao thông • Chúc quý khách và các bác tài một hành trình thượng lộ bình an, cuốc xe đắt hàng! 💚
            </marquee>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("<div style='text-align:center;color:#087f4f;font-size:18px;font-weight:900;margin:1px 0 9px;'>📍 NHẬP KHÁCH MỚI</div>", unsafe_allow_html=True)
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
        
        cache_row = [
            get_next_stt("CACHE_4567"), st.session_state.trip_id, get_vn_time(st.session_state.trip_started_at), "---", "---",                              
            st.session_state.cust_name, st.session_state.cust_phone, 0, st.session_state['user_name'], DONG_GIA, 0, 0, "BẮT ĐẦU CUỐC"                      
        ]
        append_row_to_sheet("CACHE_4567", cache_row)[0]
        update_driver_status(st.session_state["user_phone"], "Đang chạy xe")
        st.rerun()

# ---> TRẠNG THÁI 2: ĐANG CHẠY
elif st.session_state.trip_active:
    current_start_ts = st.session_state.get('trip_started_at', time.time())
    
    html_live_tracker = f"""
    <div style="text-align: center;">
        <div class="fare-panel"><div style="color:#087f4f;font-size:17px;font-weight:900;">CƯỚC PHÍ TẠM TÍNH</div>
        <div id="price" style="color: #10b981; font-size: 55px; font-weight: 900; margin: 10px 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);">0 đ</div>
        <div style="color:#52655d;font-size:17px;margin-bottom:6px;"><span id="km" style="font-weight:900;color:#0f172a;">0.00</span> km • {DONG_GIA:,.0f} đ/km</div></div>
        
        <button id="btnStop" onclick="stopTripNow()" style="width: 100%; background: #ef4444; color: white; border: none; border-radius: 12px; padding: 20px; font-size: 22px; font-weight: 900; cursor: pointer; box-shadow: 0 5px 15px rgba(239, 68, 68, 0.4);">
            🛑 KẾT THÚC CHUYẾN ĐI
        </button>
        <div id="debug_acc" style="font-size: 12px; color: #94a3b8; margin-top: 15px;">Đang tìm GPS...</div>
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
                document.getElementById("debug_acc").innerText = "Độ lệch GPS: ±" + acc.toFixed(1) + " m";
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
        try {{ parentUrl = new URL(window.parent.location.href); }} 
        catch(e) {{ parentUrl = new URL(window.location.href); }}
        
        parentUrl.searchParams.set("action", "stop");
        parentUrl.searchParams.set("dist", finalDist);
        parentUrl.searchParams.set("start", "{current_start_ts}");
        parentUrl.searchParams.set("cname", "{st.session_state.get('cust_name', 'Khách vãng lai')}");
        parentUrl.searchParams.set("cphone", "{st.session_state.get('cust_phone', '')}");
        
        try {{ window.top.location.href = parentUrl.toString(); }} 
        catch(e) {{ window.location.href = parentUrl.toString(); }}
    }}
    </script>
    """
    components.html(html_live_tracker, height=300)

# ---> TRẠNG THÁI 3: KẾT THÚC
elif not st.session_state.trip_active and st.session_state.trip_ended_at:
    if st.session_state.get("end_trip_effect"):
        st.toast("Đã chốt chuyến và lưu doanh thu.", icon="✅")
        st.session_state["end_trip_effect"] = False

    km = st.session_state.trip_total_m / 1000.0
    fare = round(km * DONG_GIA)
    
    st.markdown("<div class='receipt-print-area'>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="receipt-box">
            <div style="font-size: 22px; font-weight: 900; color: #0f172a; margin-bottom: 5px;">🛵 4567 XE ÔM</div>
            <div style="color:#64748b; font-size:14px; margin-bottom:15px;">HÓA ĐƠN CHUYẾN ĐI</div>
            <div style="text-align: left; font-size:16px; line-height:1.8;">
                <b>Khách hàng:</b> {st.session_state.get('cust_name', 'Khách vãng lai')}<br>
                <b>Đơn giá:</b> {DONG_GIA:,.0f} đ/km<br>
                <b>Quãng đường:</b> {km:.2f} km<br>
                <hr style="margin: 10px 0; border: 1px dashed #cbd5e1;">
                <div style="font-size:28px; font-weight:900; color:#10b981; text-align:center; padding: 10px 0;">
                    {fare:,.0f} VNĐ
                </div>
            </div>
            <div style="margin-top:10px; font-size:14px; font-style:italic;">Cảm ơn quý khách!</div>
        </div>
        """, unsafe_allow_html=True
    )
    
    if st.button("♻️ VỀ TRANG CHỦ / NHẬN CUỐC", type="primary", use_container_width=True):
        reset_trip()
        st.rerun()


# ============================================================
# 7. KHU VỰC HỖ TRỢ VÀ ĐĂNG XUẤT
# ============================================================
with st.expander("🔧 Kiểm tra kết nối Google Sheets", expanded=False):
    if st.button("🧪 KIỂM TRA DATA_4567", use_container_width=True):
        try:
            client = init_google_sheet_client()
            sheet = client.open_by_key(SHEET_KEY)
            ws = sheet.worksheet("DATA_4567")
            headers = ws.row_values(1)
            st.success(f"✅ Kết nối Google Sheets OK • DATA_4567 tồn tại • {len(headers)} cột.")
        except Exception as exc:
            st.error(f"❌ Kết nối DATA_4567 thất bại: {type(exc).__name__}: {exc}")

st.markdown("<div class='support-title'>HỖ TRỢ KHI CẦN THIẾT</div>", unsafe_allow_html=True)
c_sos, c_zalo = st.columns(2)
with c_sos:
    st.markdown('<a href="tel:0978666620" class="btn-sos">🚨 SOS</a>', unsafe_allow_html=True)
with c_zalo:
    st.markdown('<a href="https://zalo.me/0978666620" class="btn-zalo" target="_blank">💬 ZALO</a>', unsafe_allow_html=True)

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
        append_row_to_sheet("DATA_4567", row_data)
        delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)

    update_driver_status(st.session_state["user_phone"], "Ngoại tuyến")
    
    st.session_state["logged_in"] = False
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()
