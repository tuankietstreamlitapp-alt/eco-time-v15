from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="4567 Xe Ôm - Google Sheets Cache",
    page_icon="🛵",
    layout="centered",
)

# ============================================================
# CẤU HÌNH KẾT NỐI GOOGLE SHEETS
# ============================================================
@st.cache_resource
def init_google_sheets():
  try:
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["type"] = "service_account"

    # --- BỘ LỌC TỰ ĐỘNG SỬA LỖI BASE64 KHI COPY TRÊN ĐIỆN THOẠI ---
    raw_key = creds_dict.get("private_key", "")
    if "-----BEGIN PRIVATE KEY-----" in raw_key:
        key_body = raw_key.split("-----BEGIN PRIVATE KEY-----")[1].split("-----END PRIVATE KEY-----")[0]
        key_body = key_body.replace(" ", "").replace("\\n", "").replace("\n", "").replace("\r", "")
        
        chunks = [key_body[i:i+64] for i in range(0, len(key_body), 64)]
        clean_key = "-----BEGIN PRIVATE KEY-----\n" + "\n".join(chunks) + "\n-----END PRIVATE KEY-----\n"
        creds_dict["private_key"] = clean_key
    # --------------------------------------------------------------

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    SHEET_URL = "https://docs.google.com/spreadsheets/d/1A3-1am25vZLN57SD7pkfxxQtymCaPnCj9HgBpw5RcTY/edit?usp=drivesdk"
    sheet_file = client.open_by_url(SHEET_URL)
    return (
        sheet_file.worksheet("CACHE"),
        sheet_file.worksheet("DATA"),
        sheet_file.worksheet("DANGNHAP"),
        True,
    )
  except Exception as e:
    return None, None, None, str(e)

sheet_cache, sheet_data, sheet_login, is_connected = init_google_sheets()

# ============================================================
# CSS TỐI ƯU GIAO DIỆN
# ============================================================
st.markdown(
    """
    <style>
    .stApp { background-color: #f1f5f9; }
    
    .block-container { 
        max-width: 500px; 
        padding-top: 1rem !important; 
        padding-bottom: 2rem; 
        padding-left: 1rem; 
        padding-right: 1rem; 
    }
    
    header { visibility: hidden; }
    
    div.stButton > button { 
        border-radius: 14px !important; 
        font-weight: 900 !important; 
        font-size: 22px !important; 
        min-height: 60px !important; 
    }
    
    .app-card { 
        background: #ffffff; 
        border-radius: 18px; 
        padding: 20px; 
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04); 
        margin-top: 10px; 
        margin-bottom: 15px; 
        border: 1px solid #e2e8f0; 
    }
    
    .stTextInput input, .stSelectbox select {
        background-color: #f8fafc !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 12px !important;
        font-size: 16px !important;
        color: #1e293b !important;
        padding: 10px 14px !important;
    }
    
    .btn-zalo-single { 
        background: #0284c7; 
        color: white !important; 
        padding: 14px; 
        border-radius: 14px; 
        text-align: center; 
        font-weight: bold; 
        font-size: 18px; 
        display: block; 
        text-decoration: none; 
        box-shadow: 0 4px 10px rgba(2, 132, 199, 0.2);
    }
    .btn-zalo-single:hover { opacity: 0.9; color: white !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Khởi tạo trạng thái phiên làm việc
if "logged_in" not in st.session_state:
  st.session_state.logged_in = False
if "driver_name" not in st.session_state:
  st.session_state.driver_name = ""
if "mock_state" not in st.session_state:
  st.session_state.mock_state = "home"
if "customer_name" not in st.session_state:
  st.session_state.customer_name = ""
if "customer_phone" not in st.session_state:
  st.session_state.customer_phone = ""
if "ma_cuoc_xe" not in st.session_state:
  st.session_state.ma_cuoc_xe = ""
if "start_time_str" not in st.session_state:
  st.session_state.start_time_str = ""

UNIT_PRICE = 5000  # 5,000 đ/km

# ============================================================
# 1. MÀN HÌNH ĐĂNG NHẬP (DỰA TRÊN SHEET DANGNHAP)
# ============================================================
if not st.session_state.logged_in:
  st.markdown(
      "<h1 style='text-align:center; color:#059669; margin-bottom:10px;"
      " font-size:28px;'>🛵 4567 XE ÔM</h1>",
      unsafe_allow_html=True,
  )
  st.markdown("<div class='app-card'>", unsafe_allow_html=True)
  st.markdown(
      "<div style='font-size:18px; font-weight:900; color:#059669;"
      " margin-bottom:12px; padding-bottom:8px; border-bottom:2px solid"
      " #f1f5f9; text-align:center;'>🔐 ĐĂNG NHẬP TÀI XẾ</div>",
      unsafe_allow_html=True,
  )

  # Lấy danh sách tài xế từ sheet DANGNHAP (Cột 3 tương ứng với 'TÀI XẾ')
  driver_list = []
  if is_connected is True and sheet_login:
    try:
      login_rows = sheet_login.get_all_values()
      if len(login_rows) > 1:
        # Giả sử cấu trúc cột: STT(0), SĐTTÊN(1), TÀI XẾ(2), HIỆN TRẠNG TÀI XẾ(3)
        for row in login_rows[1:]:
          if len(row) > 2 and row[2].strip():
            driver_list.append(row[2].strip())
    except Exception:
      pass

  if not driver_list:
    driver_list = ["Nguyễn Văn A", "Trần Văn B"]  # Dự phòng nếu sheet trống

  selected_driver = st.selectbox("CHỌN TÀI XẾ:", driver_list)
  input_pass = st.text_input("MÃ XÁC THỰC / SĐT:", type="password", placeholder="Nhập để xác nhận...")

  st.write("")
  if st.button("🚀 ĐĂNG NHẬP", type="primary", use_container_width=True):
    st.session_state.logged_in = True
    st.session_state.driver_name = selected_driver
    st.rerun()

  st.markdown("</div>", unsafe_allow_html=True)

  # Nút Zalo hỗ trợ ở màn hình đăng nhập
  st.markdown("<div style='margin-top: 15px;'>", unsafe_allow_html=True)
  st.markdown(
      '<a href="https://zalo.me/0978666620" class="btn-zalo-single"'
      ' target="_blank">💬 LIÊN HỆ HỖ TRỢ ZALO</a>',
      unsafe_allow_html=True,
  )
  st.markdown("</div>", unsafe_allow_html=True)

else:
  # ============================================================
  # HỆ THỐNG CHÍNH SAU KHI ĐĂNG NHẬP THÀNH CÔNG
  # ============================================================

  # Kiểm tra CACHE phòng hờ tài xế lỡ tay refresh app
  if (
      st.session_state.mock_state == "home"
      and is_connected is True
      and sheet_cache
  ):
    try:
      cache_rows = sheet_cache.get_all_values()
      if len(cache_rows) > 1:
        last_row = cache_rows[1] 
        if len(last_row) >= 13:
          trang_thai = last_row[12] if len(last_row) > 12 else ""
          if trang_thai == "Đang chạy":
            st.session_state.ma_cuoc_xe = last_row[1]
            st.session_state.start_time_str = last_row[2]
            st.session_state.customer_name = last_row[5]
            st.session_state.customer_phone = last_row[6]
            st.session_state.mock_state = "running" 
    except Exception:
      pass

  # Kiểm tra query params từ Python (xử lý sự kiện thanh toán)
  query_params = st.query_params
  action_trigger = query_params.get("action", None)

  if action_trigger == "pay":
    if is_connected is True and sheet_cache and sheet_data:
      try:
        cache_rows = sheet_cache.get_all_values()
        if len(cache_rows) > 1:
          row_to_move = cache_rows[1] 
          if len(row_to_move) > 12:
            row_to_move[12] = "Đã thanh toán"
          sheet_data.append_row(row_to_move) 
          sheet_cache.batch_clear(['A2:M100'])
      except Exception as e:
        print("Lỗi clear cache:", e)

    st.session_state.mock_state = "home"
    st.session_state.customer_name = ""
    st.session_state.customer_phone = ""
    st.session_state.ma_cuoc_xe = ""
    st.session_state.start_time_str = ""
    st.query_params.clear()
    st.rerun()

  # TIÊU ĐỀ APP & THANH THÔNG TIN TÀI XẾ + NÚT ĐĂNG XUẤT
  st.markdown(
      "<h1 style='text-align:center; color:#059669; margin-bottom:0px;"
      " font-size:28px;'>🛵 4567 XE ÔM</h1>",
      unsafe_allow_html=True,
  )

  col_info, col_logout = st.columns([3, 1])
  with col_info:
    if is_connected is True:
      st.markdown(
          f"<div style='font-size:13px; color:#64748b; margin-top:6px;'>Tài xế: <b>{st.session_state.driver_name}</b> <br><span"
          " style='color:#10b981;'>● Kết nối Sheets thành công</span></div>",
          unsafe_allow_html=True,
      )
  with col_logout:
    if st.button("🚪 THOÁT", use_container_width=True):
      st.session_state.logged_in = False
      st.session_state.driver_name = ""
      st.session_state.mock_state = "home"
      st.rerun()

  st.markdown("<hr style='margin: 10px 0px 15px 0px;'>", unsafe_allow_html=True)

  # -------------------------------------------------------------------------
  # 1. MÀN HÌNH CHỜ (NHẬP KHÁCH & BẮT ĐẦU)
  # -------------------------------------------------------------------------
  if st.session_state.mock_state == "home":
    st.markdown("<div class='app-card'>", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:18px; font-weight:900; color:#059669;"
        " margin-bottom:12px; padding-bottom:8px; border-bottom:2px solid"
        " #f1f5f9; text-align:center;'>🚖 TẠO CUỐC XE MỚI</div>",
        unsafe_allow_html=True,
    )

    c_name = st.text_input(
        "TÊN KHÁCH HÀNG:",
        placeholder="Ví dụ: Anh Nam (Bỏ trống nếu vãng lai)",
        key="input_name",
    )
    c_phone = st.text_input(
        "SỐ ĐIỆN THOẠI:",
        placeholder="Ví dụ: 0909xxxxxx",
        key="input_phone",
    )

    st.write("")
    if st.button("🟢 BẮT ĐẦU CHẠY", type="primary", use_container_width=True):
      st.session_state.customer_name = (
          c_name.strip() if c_name.strip() else "Khách vãng lai"
      )
      st.session_state.customer_phone = (
          c_phone.strip() if c_phone.strip() else "Không có"
      )

      vn_now = datetime.utcnow() + timedelta(hours=7)
      st.session_state.ma_cuoc_xe = f"CX_{vn_now.strftime('%Y%m%d_%H%M%S')}"
      st.session_state.start_time_str = vn_now.strftime("%Y-%m-%d %H:%M:%S")

      if is_connected is True and sheet_cache:
        try:
          new_row = [
              "1",
              st.session_state.ma_cuoc_xe,
              st.session_state.start_time_str,
              "",
              "",
              st.session_state.customer_name,
              st.session_state.customer_phone,
              "0",
              st.session_state.driver_name,
              str(UNIT_PRICE),
              "0",
              "0",
              "Đang chạy",
          ]
          sheet_cache.append_row(new_row)
        except Exception as e:
          st.error(f"Lỗi ghi Cache: {e}")

      st.session_state.mock_state = "running"
      st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

  # -------------------------------------------------------------------------
  # 2. MÀN HÌNH ĐANG CHẠY & THANH TOÁN (TÍCH HỢP GPS)
  # -------------------------------------------------------------------------
  elif st.session_state.mock_state == "running":
    if action_trigger == "end":
      final_km = query_params.get("km", "0")
      final_time = query_params.get("time", "00:00:00")
      final_money = query_params.get("money", "0")

      if is_connected is True and sheet_cache:
        try:
          cell = sheet_cache.find(st.session_state.ma_cuoc_xe)
          if cell:
            row_idx = cell.row
            vn_now = datetime.utcnow() + timedelta(hours=7)
            end_time_str = vn_now.strftime("%Y-%m-%d %H:%M:%S")
            sheet_cache.update_cell(row_idx, 4, end_time_str)  
            sheet_cache.update_cell(row_idx, 5, final_time)  
            sheet_cache.update_cell(row_idx, 11, final_km)  
            sheet_cache.update_cell(row_idx, 12, final_money)  
            sheet_cache.update_cell(row_idx, 13, "Chờ thanh toán") 
        except Exception:
          pass

    gps_component_code = f"""
      <!DOCTYPE html>
      <html>
      <head>
      <meta charset="utf-8">
      <style>
          body {{ font-family: sans-serif; background: transparent; margin: 0; padding: 0; }}
          .app-card {{ background: #ffffff; border-radius: 18px; padding: 20px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04); border: 1px solid #e2e8f0; }}
          .metric-row {{ font-size: 18px; font-weight: bold; color: #334155; padding: 12px 0; border-bottom: 2px dashed #f1f5f9; display: flex; justify-content: space-between; align-items: center; }}
          .btn-action {{ width: 100%; padding: 16px; border-radius: 14px; font-weight: 900; font-size: 22px; cursor: pointer; margin-top: 15px; border: none; box-sizing: border-box; text-align: center; text-decoration: none; display: block; }}
          .btn-end {{ background: #dc2626; color: white; box-shadow: 0 4px 10px rgba(220, 38, 38, 0.3); }}
          .btn-pay {{ background: #059669; color: white; box-shadow: 0 4px 10px rgba(5, 150, 105, 0.3); }}
          .btn-action:hover {{ opacity: 0.9; color: white; }}
          .gps-status {{ font-size: 13px; color: #10b981; text-align: center; margin-bottom: 12px; font-weight: bold; background: #ecfdf5; padding: 8px; border-radius: 8px; border: 1px solid #a7f3d0; }}
          .customer-tag {{ font-size: 14px; color: #0284c7; background: #f0f9ff; padding: 6px 12px; border-radius: 8px; margin-bottom: 12px; text-align: center; font-weight: bold; border: 1px solid #bae6fd; }}
      </style>
      </head>
      <body>
      <div class="app-card">
          <!-- GIAO DIỆN ĐANG CHẠY -->
          <div id="running-view">
              <div style="font-size:18px; font-weight:900; color:#059669; margin-bottom:6px; text-align:center;">⏱️ ĐANG TRONG CUỐC XE...</div>
              <div class="customer-tag">Khách: {st.session_state.customer_name} ({st.session_state.customer_phone})</div>
              <div id="status" class="gps-status">🛰️ Đang kết nối tín hiệu vệ tinh...</div>
              
              <div class="metric-row">
                  <span>SỐ KM:</span>
                  <span id="km-val" style="color:#0284c7;">0.00 km</span>
              </div>
              <div class="metric-row">
                  <span>THỜI GIAN ĐI:</span>
                  <span id="time-val" style="color:#059669;">00:00:00</span>
              </div>
              <div class="metric-row">
                  <span>ĐƠN GIÁ:</span>
                  <span>{UNIT_PRICE:,} đ/km</span>
              </div>
              <div class="metric-row" style="font-size:21px; color:#dc2626; border-bottom: none;">
                  <span>THÀNH TIỀN:</span>
                  <span id="money-val" style="font-weight:900;">0 đ</span>
              </div>

              <button class="btn-action btn-end" onclick="endTrip()">🛑 KẾT THÚC CHUYẾN ĐI</button>
          </div>

          <!-- GIAO DIỆN THANH TOÁN -->
          <div id="payment-view" style="display: none;">
              <div style="font-size:18px; font-weight:900; color:#059669; margin-bottom:6px; text-align:center;">💳 XÁC NHẬN THANH TOÁN</div>
              <div class="customer-tag">Khách: {st.session_state.customer_name} ({st.session_state.customer_phone})</div>
              <div style="font-size: 13px; color: #64748b; text-align: center; margin-bottom: 12px; font-weight: bold; background: #f1f5f9; padding: 8px; border-radius: 8px;">📋 Đã chốt chuyến. Bấm thanh toán để tạo cuốc mới!</div>
              
              <div class="metric-row">
                  <span>SỐ KM:</span>
                  <span id="final-km-val" style="color:#0284c7;">0.00 km</span>
              </div>
              <div class="metric-row">
                  <span>THỜI GIAN ĐI:</span>
                  <span id="final-time-val" style="color:#059669;">00:00:00</span>
              </div>
              <div class="metric-row">
                  <span>ĐƠN GIÁ:</span>
                  <span>{UNIT_PRICE:,} đ/km</span>
              </div>
              <div class="metric-row" style="font-size:21px; color:#059669; border-bottom: none;">
                  <span>THÀNH TIỀN:</span>
                  <span id="final-money-val" style="font-weight:900;">0 đ</span>
              </div>

              <a id="pay-link" href="#" target="_top" class="btn-action btn-pay">✅ XÁC NHẬN THANH TOÁN & TẠO CUỐC MỚI</a>
          </div>
      </div>

      <script>
          let watchId = null;
          let prevLat = null;
          let prevLon = null;
          let totalDist = 0; 
          let unitPrice = {UNIT_PRICE};
          let seconds = 0;
          
          let timerInterval = setInterval(() => {{
              seconds++;
              let h = String(Math.floor(seconds / 3600)).padStart(2, '0');
              let m = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
              let s = String(seconds % 60).padStart(2, '0');
              document.getElementById('time-val').innerText = h + ":" + m + ":" + s;
          }}, 1000);

          function getDistanceFromLatLonInKm(lat1, lon1, lat2, lon2) {{
              let R = 6371; 
              let dLat = deg2rad(lat2 - lat1);
              let dLon = deg2rad(lon2 - lon1);
              let a = 
                  Math.sin(dLat/2) * Math.sin(dLat/2) +
                  Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) * 
                  Math.sin(dLon/2) * Math.sin(dLon/2); 
              let c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a)); 
              return R * c;
          }}

          function deg2rad(deg) {{
              return deg * (Math.PI / 180);
          }}

          if (navigator.geolocation) {{
              watchId = navigator.geolocation.watchPosition(
                  (position) => {{
                      let lat = position.coords.latitude;
                      let lon = position.coords.longitude;
                      let accuracy = position.coords.accuracy;

                      if (prevLat !== null && prevLon !== null) {{
                          let dist = getDistanceFromLatLonInKm(prevLat, prevLon, lat, lon);
                          if (dist > 0.003 && accuracy < 50) {{
                              totalDist += dist;
                          }}
                      }}
                      prevLat = lat;
                      prevLon = lon;

                      let money = Math.round(totalDist * unitPrice);
                      document.getElementById('km-val').innerText = totalDist.toFixed(2) + " km";
                      document.getElementById('money-val').innerText = money.toLocaleString('vi-VN') + " đ";
                  }},
                  (error) => {{
                      document.getElementById('status').innerText = "⚠️ Lỗi GPS: Hãy bật định vị!";
                  }},
                  {{ enableHighAccuracy: true, maximumAge: 0, timeout: 5000 }}
              );
          }}

          function endTrip() {{
              if (watchId !== null) {{
                  navigator.geolocation.clearWatch(watchId);
              }}
              clearInterval(timerInterval);

              let finalKmStr = totalDist.toFixed(2);
              let finalTimeStr = document.getElementById('time-val').innerText;
              let finalMoneyNum = Math.round(totalDist * unitPrice);

              document.getElementById('final-km-val').innerText = finalKmStr + " km";
              document.getElementById('final-time-val').innerText = finalTimeStr;
              document.getElementById('final-money-val').innerText = finalMoneyNum.toLocaleString('vi-VN') + " đ";

              document.getElementById('running-view').style.display = 'none';
              document.getElementById('payment-view').style.display = 'block';

              let payUrl = window.location.pathname + '?action=pay';
              document.getElementById('pay-link').setAttribute('href', payUrl);

              let urlParams = new URLSearchParams(window.location.search);
              urlParams.set('action', 'end');
              urlParams.set('km', finalKmStr);
              urlParams.set('time', finalTimeStr);
              urlParams.set('money', finalMoneyNum);
              
              fetch(window.location.pathname + '?' + urlParams.toString()).catch(() => {{}});
          }}
      </script>
      </body>
      </html>
      """
    components.html(gps_component_code, height=480)

  # ============================================================
  # NÚT ZALO & CÂU CHÚC Ở TẬN CÙNG DƯỚI ĐÁY
  # ============================================================
  st.markdown("<div style='margin-top: 15px;'>", unsafe_allow_html=True)
  st.markdown(
      '<a href="https://zalo.me/0978666620" class="btn-zalo-single"'
      ' target="_blank">💬 LIÊN HỆ HỖ TRỢ ZALO</a>',
      unsafe_allow_html=True,
  )
  st.markdown("</div>", unsafe_allow_html=True)

  st.markdown(
      """
      <div style='background: #ecfdf5; border: 1.5px solid #10b981; border-radius: 12px; padding: 12px; text-align: center; margin-top: 15px;'>
          <span style='color: #047857; font-weight: bold; font-size: 15px;'>🌟 Chúc ní một ngày chạy xe bội thu, khách đông nườm nượp!</span>
      </div>
  """,
      unsafe_allow_html=True,
  )
