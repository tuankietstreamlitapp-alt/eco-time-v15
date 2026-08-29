from datetime import datetime, timedelta
import math
import time
import urllib.parse
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="4567 Xe Ôm - Google Sheets Edition",
    page_icon="🛵",
    layout="centered",
)

# ============================================================
# CẤU HÌNH KẾT NỐI GOOGLE SHEETS (AN TOÀN TUYỆT ĐỐI KHÔNG CRASH)
# ============================================================
try:
    if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
        SHEET_KEY = st.secrets["connections"]["gsheets"].get("spreadsheet", "1A3-1am25vZLN57SD7pkfxxQtymCaPnCj9HgBpw5RcTY")
    else:
        SHEET_KEY = "1A3-1am25vZLN57SD7pkfxxQtymCaPnCj9HgBpw5RcTY"
except Exception:
    SHEET_KEY = "1A3-1am25vZLN57SD7pkfxxQtymCaPnCj9HgBpw5RcTY"

@st.cache_resource
def init_google_sheet_client():
  try:
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    
    creds_dict = {}
    if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
        creds_dict = dict(st.secrets["connections"]["gsheets"])
    elif "gsheets" in st.secrets:
        creds_dict = dict(st.secrets["gsheets"])
    else:
        creds_dict = dict(st.secrets)

    if not creds_dict.get("client_email") or not creds_dict.get("private_key"):
        return None

    if "token_uri" not in creds_dict:
        creds_dict["token_uri"] = "https://oauth2.googleapis.com/token"
    if "auth_uri" not in creds_dict:
        creds_dict["auth_uri"] = "https://accounts.google.com/authorize"
    if "type" not in creds_dict:
        creds_dict["type"] = "service_account"

    raw_key = creds_dict.get("private_key", "")
    if "-----BEGIN PRIVATE KEY-----" in raw_key:
        key_body = raw_key.split("-----BEGIN PRIVATE KEY-----")[1].split("-----END PRIVATE KEY-----")[0]
        key_body = key_body.replace(" ", "").replace("\\n", "").replace("\n", "").replace("\r", "")
        chunks = [key_body[i:i+64] for i in range(0, len(key_body), 64)]
        clean_key = "-----BEGIN PRIVATE KEY-----\n" + "\n".join(chunks) + "\n-----END PRIVATE KEY-----\n"
        creds_dict["private_key"] = clean_key

    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client
  except Exception:
    return None

def get_worksheet_data(tab_name):
  try:
    client = init_google_sheet_client()
    if not client:
      return None, []
    sheet = client.open_by_key(SHEET_KEY)
    ws = sheet.worksheet(tab_name)
    return ws, ws.get_all_records()
  except Exception:
    return None, []

def append_row_to_sheet(tab_name, row_values):
  try:
    client = init_google_sheet_client()
    if not client:
      return False
    sheet = client.open_by_key(SHEET_KEY)
    ws = sheet.worksheet(tab_name)
    ws.append_row(row_values)
    return True
  except Exception:
    return False

def clear_cache_sheet():
  try:
    client = init_google_sheet_client()
    if not client:
      return False
    sheet = client.open_by_key(SHEET_KEY)
    ws = sheet.worksheet("CACHE")
    ws.batch_clear(['A2:N100'])
    return True
  except Exception:
    return False

# ============================================================
# CSS GIAO DIỆN XANH SM
# ============================================================
st.markdown(
    """
    <style>
    .stApp { background-color: #f8fafc; }
    .block-container { max-width: 500px; padding-top: 1rem; padding-bottom: 2rem; padding-left: 1rem; padding-right: 1rem; }
    header { visibility: hidden; }
    .app-header {
        background: linear-gradient(135deg, #059669 0%, #047857 100%);
        padding: 16px 20px; border-radius: 16px; color: white; margin-bottom: 14px;
        box-shadow: 0 4px 15px rgba(5, 150, 105, 0.2);
    }
    .app-title { font-size: 20px; font-weight: 900; margin: 0; color: white; }
    .app-subtitle { margin: 2px 0 0 0; color: #e2e8f0; font-size: 12px; font-weight: 500; }
    .status-badge { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; background: rgba(255, 255, 255, 0.2); color: #ffffff; margin-top: 6px; }
    .section-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 18px; margin-bottom: 14px; box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04); }
    .section-title { font-size: 15px; font-weight: 800; color: #0f172a; margin-bottom: 4px; text-transform: uppercase; }
    .section-desc { font-size: 13px; color: #64748b; margin-bottom: 12px; line-height: 1.4; }
    div.stButton > button {
        border-radius: 12px !important; font-weight: 800 !important; min-height: 50px !important;
        background-color: #059669 !important; color: white !important; border: none !important;
        box-shadow: 0 4px 12px rgba(5, 150, 105, 0.2);
    }
    div.stButton > button:hover { background-color: #047857 !important; }
    .stTextInput input, .stSelectbox select {
        background-color: #f8fafc !important; border: 1.5px solid #cbd5e1 !important; border-radius: 12px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# KHỞI TẠO SESSION STATE & TỰ ĐỘNG ĐĂNG NHẬP QUA URL
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
    "show_balloons": False
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

UNIT_PRICE = 5000  # VNĐ / km
GPS_ACCURACY_MAX_M = 50
MIN_MOVE_M = 3

if not st.session_state["logged_in"] and "phone" in st.query_params:
  saved_phone = st.query_params["phone"]
  if saved_phone:
    st.session_state["logged_in"] = True
    st.session_state["user_phone"] = str(saved_phone)
    st.session_state["user_name"] = str(saved_phone)

# ============================================================
# XỬ LÝ SỰ KIỆN KẾT THÚC CHUYẾN TỪ JAVASCRIPT GỬI VỀ
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

  cust_info = st.query_params.get("cust", "Khách vãng lai")
  
  vn_now = datetime.utcnow() + timedelta(hours=7)
  start_time_str = datetime.fromtimestamp(start_ts).strftime('%Y-%m-%d %H:%M:%S')
  end_time_str = vn_now.strftime('%Y-%m-%d %H:%M:%S')
  
  km_val = round(dist_val / 1000.0, 2)
  fare_val = round(km_val * UNIT_PRICE)
  trip_id = f"CX_{int(start_ts)}"

  _, data_records = get_worksheet_data("DATA")
  next_data_stt = len(data_records) + 1

  row_data = [
      str(next_data_stt),
      trip_id,
      start_time_str,
      end_time_str,
      cust_info,
      "Không có",
      km_val,
      UNIT_PRICE,
      fare_val,
      st.session_state['user_name'],
      "Đã thanh toán"
  ]
  
  append_row_to_sheet("DATA", row_data)
  clear_cache_sheet()

  st.session_state.trip_active = False
  st.session_state.trip_ended_at = time.time()
  st.session_state.trip_total_m = dist_val
  st.session_state.customer_info = cust_info
  st.session_state["show_balloons"] = True

  phone_val = st.query_params.get("phone", "")
  st.query_params.clear()
  if phone_val:
    st.query_params["phone"] = phone_val
  st.rerun()

# ============================================================
# 1. MÀN HÌNH ĐĂNG NHẬP
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
  
  client_check = init_google_sheet_client()
  if not client_check:
      st.warning("⚠️ Chưa cấu hình Secrets Google Sheets trên Streamlit Cloud. App đang chạy ở chế độ mô phỏng giao diện.")

  st.markdown(
      """
      <div class="section-card">
          <div class="section-title">🔐 Đăng nhập tài xế</div>
          <div class="section-desc">Chọn hoặc nhập tên tài xế để bắt đầu ca làm việc.</div>
      </div>
      """,
      unsafe_allow_html=True,
  )

  driver_names = []
  _, login_records = get_worksheet_data("DANGNHAP")
  if login_records:
    for row in login_records:
      name = str(row.get("TÀI XẾ", "")).strip()
      if name and name not in driver_names:
        driver_names.append(name)
  
  if not driver_names:
    driver_names = ["Nguyễn Văn A", "Trần Văn B", "Tài Xế 4567"]

  selected_driver = st.selectbox("CHỌN TÀI XẾ:", driver_names)
  remember_me = st.checkbox("Ghi nhớ đăng nhập", value=True)

  if st.button("🚀 ĐĂNG NHẬP HỆ THỐNG", use_container_width=True):
    st.session_state["logged_in"] = True
    st.session_state["user_phone"] = selected_driver
    st.session_state["user_name"] = selected_driver
    if remember_me:
      st.query_params["phone"] = selected_driver
    st.success(f"Xin chào tài xế **{selected_driver}**!")
    time.sleep(0.5)
    st.rerun()

  st.stop()

# ============================================================
# 2. GIAO DIỆN CHÍNH SAU KHI ĐĂNG NHẬP
# ============================================================
col_info, col_logout = st.columns([3, 1], vertical_alignment="center")
with col_info:
  st.markdown(
      f"""
      <div class="app-header" style="margin-bottom:0; padding: 10px 14px;">
          <div style="font-size: 15px; font-weight: 800;">Tài xế: {st.session_state['user_name']}</div>
          <div class="status-badge">● Đã đăng nhập hệ thống</div>
      </div>
      """,
      unsafe_allow_html=True,
  )
with col_logout:
  if st.button("🚪 THOÁT", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["user_phone"] = ""
    st.session_state["user_name"] = ""
    st.query_params.clear()
    st.rerun()

st.write("")

def reset_trip():
  st.session_state.trip_active = False
  st.session_state.trip_started_at = None
  st.session_state.trip_ended_at = None
  st.session_state.trip_total_m = 0.0
  st.session_state.show_balloons = False

# TRẠNG THÁI: CHƯA CHẠY / SẴN SÀNG
if not st.session_state.trip_active and not st.session_state.trip_ended_at:
  st.markdown(
      """
      <div class="section-card">
          <div class="section-title">🚖 TẠO CUỐC XE MỚI</div>
          <div class="section-desc">Nhập thông tin khách hàng và bấm bắt đầu để kích hoạt bộ đo GPS thời gian thực.</div>
      </div>
      """,
      unsafe_allow_html=True,
  )

  c_name = st.text_input("TÊN KHÁCH HÀNG:", placeholder="Ví dụ: Anh Nam (Bỏ trống nếu vãng lai)")
  c_phone = st.text_input("SỐ ĐIỆN THOẠI:", placeholder="Ví dụ: 0909xxxxxx")

  if st.button("🟢 BẮT ĐẦU CHẠY", use_container_width=True):
    reset_trip()
    st.session_state.trip_active = True
    st.session_state.trip_started_at = time.time()
    st.session_state.customer_info = c_name.strip() if c_name.strip() else "Khách vãng lai (Không có)"
    st.session_state.trip_id = f"CX_{int(st.session_state.trip_started_at)}"
    
    vn_now = datetime.utcnow() + timedelta(hours=7)
    start_time_str = vn_now.strftime('%Y-%m-%d %H:%M:%S')
    
    _, cache_records = get_worksheet_data("CACHE")
    next_cache_stt = len(cache_records) + 1

    cache_row = [
        str(next_cache_stt),
        st.session_state.trip_id,
        start_time_str,
        "",
        "",
        st.session_state.customer_info,
        c_phone.strip() if c_phone.strip() else "Không có",
        "0",
        st.session_state['user_name'],
        str(UNIT_PRICE),
        "0",
        "0",
        "Đang chạy"
    ]
    append_row_to_sheet("CACHE", cache_row)
    st.rerun()

# TRẠNG THÁI: ĐANG TRONG HÀNH TRÌNH
elif st.session_state.trip_active:
  current_start_ts = st.session_state.get('trip_started_at', time.time())
  cust_display = st.session_state.get('customer_info', 'Khách vãng lai (Không có)')
  cust_param = urllib.parse.quote(cust_display)

  html_live_tracker = f"""
  <div style="font-family: system-ui, -apple-system, sans-serif; padding: 20px; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);">
      <div style="text-align: center; font-size: 17px; font-weight: 900; color: #059669; margin-bottom: 12px; text-transform: uppercase;">
          ⏱️ ĐANG TRONG CUỐC XE...
      </div>

      <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 10px; margin-bottom: 8px; text-align: center; color: #166534; font-size: 13px; font-weight: 700;">
          Khách: {cust_display}
      </div>

      <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 10px; margin-bottom: 14px; text-align: center; color: #047857; font-size: 12px; font-weight: 700;">
          🛰️ <span id="debug_acc">Đang kết nối tín hiệu vệ tinh...</span>
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #f1f5f9; font-size: 15px; font-weight: 800; color: #1e293b;">
          <span>SỐ KM:</span>
          <span id="km" style="color: #0284c7; font-size: 18px; font-weight: 900;">0.00 km</span>
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #f1f5f9; font-size: 15px; font-weight: 800; color: #1e293b;">
          <span>THỜI GIAN ĐI:</span>
          <span id="stopwatch" style="color: #16a34a; font-size: 18px; font-weight: 900;">00:00:00</span>
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px dashed #cbd5e1; font-size: 15px; font-weight: 800; color: #1e293b;">
          <span>ĐƠN GIÁ:</span>
          <span style="color: #0f172a; font-size: 16px; font-weight: 800;">{UNIT_PRICE:,} đ/km</span>
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; padding: 14px 0 18px 0; font-size: 16px; font-weight: 800; color: #dc2626;">
          <span>THÀNH TIỀN:</span>
          <span id="price" style="font-size: 24px; font-weight: 900;">0 đ</span>
      </div>
      
      <button id="btnStop" onclick="stopTripNow()" style="width: 100%; background: #dc2626; color: white; border: none; border-radius: 12px; padding: 16px; font-size: 17px; font-weight: 900; cursor: pointer; box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);">
          🛑 KẾT THÚC CHUYẾN ĐI
      </button>
  </div>

  <script>
  localStorage.setItem("xeom_trip_active", "true");
  localStorage.setItem("xeom_start_time", "{current_start_ts}");

  let startTime = parseFloat("{current_start_ts}");
  setInterval(function() {{
      let now = Date.now() / 1000;
      let elapsed = Math.floor(now - startTime);
      if (elapsed < 0) elapsed = 0;
      let h = Math.floor(elapsed / 3600);
      let m = Math.floor((elapsed % 3600) / 60);
      let s = elapsed % 60;
      let formatted = String(h).padStart(2, '0') + ":" +
                      String(m).padStart(2, '0') + ":" +
                      String(s).padStart(2, '0');
      document.getElementById("stopwatch").innerText = formatted;
  }}, 1000);

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
  const unitPrice = {UNIT_PRICE};

  if (totalMeters > 0) {{
      let km = totalMeters / 1000.0;
      document.getElementById("km").innerText = km.toFixed(2) + " km";
      document.getElementById("price").innerText = Math.round(km * unitPrice).toLocaleString('vi-VN') + " đ";
  }}

  if ("geolocation" in navigator) {{
      navigator.geolocation.watchPosition(
          function(pos) {{
              let lat = pos.coords.latitude, lon = pos.coords.longitude, acc = pos.coords.accuracy;
              document.getElementById("debug_acc").innerText = "Đang kết nối tín hiệu vệ tinh... (Sai số ±" + acc.toFixed(1) + "m)";
              if (acc > {GPS_ACCURACY_MAX_M}) return;
              if (lastLat === null) {{ lastLat = lat; lastLon = lon; return; }}
              let d = calcCrow(lastLat, lastLon, lat, lon);
              if (d >= {MIN_MOVE_M} && d < 120) {{
                  totalMeters += d;
                  lastLat = lat; lastLon = lon;
                  localStorage.setItem("xeom_total_meters", totalMeters);
                  let km = totalMeters / 1000.0;
                  document.getElementById("km").innerText = km.toFixed(2) + " km";
                  document.getElementById("price").innerText = Math.round(km * unitPrice).toLocaleString('vi-VN') + " đ";
              }}
          }},
          err => {{ document.getElementById("debug_acc").innerText = "⚠️ Lỗi GPS: " + err.message; }},
          {{ enableHighAccuracy: true, maximumAge: 0, timeout: 10000 }}
      );
  }}

  function stopTripNow() {{
      let btn = document.getElementById("btnStop");
      btn.innerText = "⏳ ĐANG LƯU VÀO DATA...";
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
  # Tăng height lên 500 để nút đỏ hiện đầy đủ, không bị cắt khuất
  components.html(html_live_tracker, height=500)

# TRẠNG THÁI: HOÀN THÀNH CUỐC XE
elif not st.session_state.trip_active and st.session_state.trip_ended_at:
  if st.session_state.get("show_balloons", False):
    st.balloons()
    st.session_state["show_balloons"] = False

  km = st.session_state.trip_total_m / 1000.0
  fare = km * UNIT_PRICE

  st.markdown(
      """
      <div class="section-card" style="border-color: #059669;">
          <div class="section-title" style="color: #059669;">🎉 ĐÃ HOÀN THÀNH CUỐC XE!</div>
          <div class="section-desc">Dữ liệu chuyến đi đã được ghi nhận thành công.</div>
      </div>
      """,
      unsafe_allow_html=True,
  )

  c1, c2, c3 = st.columns(3)
  with c1: st.metric("📏 Quãng đường", f"{km:.2f} km")
  with c2: st.metric("💰 Đơn giá", f"{UNIT_PRICE:,.0f}đ")
  with c3: st.metric("💵 Thành tiền", f"{fare:,.0f} đ")

  st.info(f"👤 **Khách:** {st.session_state.get('customer_info', 'Khách vãng lai')} | 🛵 **Tài xế:** {st.session_state['user_name']}")
  
  st.write("")
  if st.button("♻️ TẠO CUỐC XE MỚI", use_container_width=True):
    reset_trip()
    st.rerun()

# ============================================================
# ZALO HỖ TRỢ
# ============================================================
st.markdown("<div style='margin-top: 15px;'>", unsafe_allow_html=True)
st.markdown(
    '<a href="https://zalo.me/0978666620" style="background: #0284c7; color: white; padding: 14px; border-radius: 12px; text-align: center; font-weight: bold; font-size: 16px; display: block; text-decoration: none; box-shadow: 0 4px 10px rgba(2, 132, 199, 0.2);" target="_blank">💬 LIÊN HỆ HỖ TRỢ ZALO</a>',
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)
