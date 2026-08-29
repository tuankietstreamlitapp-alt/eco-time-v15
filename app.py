import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="4567 Xe Ôm - Vòng Lặp Vô Hạn", page_icon="🛵", layout="centered"
)

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
    
    .stTextInput input {
        background-color: #f8fafc !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 12px !important;
        font-size: 16px !important;
        color: #1e293b !important;
        padding: 10px 14px !important;
    }
    .stTextInput input:focus {
        border-color: #059669 !important;
        box-shadow: 0 0 0 2px rgba(5, 150, 105, 0.15) !important;
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

# Khởi tạo trạng thái ứng dụng
if "mock_state" not in st.session_state:
  st.session_state.mock_state = "home"
if "customer_name" not in st.session_state:
  st.session_state.customer_name = ""
if "customer_phone" not in st.session_state:
  st.session_state.customer_phone = ""

UNIT_PRICE = 5000  # 5,000 đ/km

# TIÊU ĐỀ APP
st.markdown(
    "<h1 style='text-align:center; color:#059669; margin-bottom:0px;"
    " font-size:28px;'>🛵 4567 XE ÔM</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div style='text-align:center; font-size:15px; color:#64748b;"
    " margin-bottom:12px;'>Tài xế: <b>Nguyễn Văn A</b> &nbsp;|&nbsp; <span"
    " style='color:#10b981;'>● Sẵn sàng GPS</span></div>",
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------------
# 1. MÀN HÌNH CHỜ (NHẬP KHÁCH & BẮT ĐẦU)
# -------------------------------------------------------------------------
if st.session_state.mock_state == "home":
  #st.markdown("<div class='app-card'>", unsafe_allow_html=True)
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
    st.session_state.customer_name = c_name
    st.session_state.customer_phone = c_phone
    st.session_state.mock_state = "running"
    st.rerun()
  st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# 2. MÀN HÌNH ĐANG CHẠY & THANH TOÁN (TÍCH HỢP GPS & VÒNG LẶP)
# -------------------------------------------------------------------------
elif st.session_state.mock_state == "running":
  gps_component_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: sans-serif; background: transparent; margin: 0; padding: 0; }}
        .app-card {{ background: #ffffff; border-radius: 18px; padding: 20px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04); border: 1px solid #e2e8f0; }}
        .metric-row {{ font-size: 18px; font-weight: bold; color: #334155; padding: 12px 0; border-bottom: 2px dashed #f1f5f9; display: flex; justify-content: space-between; align-items: center; }}
        .btn-action {{ width: 100%; padding: 16px; border-radius: 14px; font-weight: 900; font-size: 22px; cursor: pointer; margin-top: 15px; border: none; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
        .btn-end {{ background: #dc2626; color: white; box-shadow: 0 4px 10px rgba(220, 38, 38, 0.3); }}
        .btn-pay {{ background: #059669; color: white; box-shadow: 0 4px 10px rgba(5, 150, 105, 0.3); }}
        .btn-action:hover {{ opacity: 0.9; }}
        .gps-status {{ font-size: 13px; color: #10b981; text-align: center; margin-bottom: 12px; font-weight: bold; background: #ecfdf5; padding: 8px; border-radius: 8px; border: 1px solid #a7f3d0; }}
    </style>
    </head>
    <body>
    <div class="app-card">
        <!-- GIAO DIỆN ĐANG CHẠY -->
        <div id="running-view">
            <div style="font-size:18px; font-weight:900; color:#059669; margin-bottom:10px; padding-bottom:8px; border-bottom:2px solid #f1f5f9; text-align:center;">⏱️ ĐANG TRONG CUỐC XE...</div>
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

        <!-- GIAO DIỆN THANH TOÁN (ĐỨNG YÊN ĐỂ MINH BẠCH) -->
        <div id="payment-view" style="display: none;">
            <div style="font-size:18px; font-weight:900; color:#059669; margin-bottom:10px; padding-bottom:8px; border-bottom:2px solid #f1f5f9; text-align:center;">💳 XÁC NHẬN THANH TOÁN</div>
            <div style="font-size: 13px; color: #64748b; text-align: center; margin-bottom: 12px; font-weight: bold; background: #f1f5f9; padding: 8px; border-radius: 8px;">📋 Thông tin đã chốt. Mời khách thanh toán!</div>
            
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

            <button class="btn-action btn-pay" onclick="confirmPayment()">✅ THANH TOÁN & NHẬN CUỐC MỚI</button>
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

        // Khi bấm KẾT THÚC CHUYẾN ĐI -> Dừng GPS, đóng băng số liệu, mở màn hình thanh toán
        function endTrip() {{
            if (watchId !== null) {{
                navigator.geolocation.clearWatch(watchId);
            }}
            clearInterval(timerInterval);

            // Chốt các con số đứng yên
            document.getElementById('final-km-val').innerText = totalDist.toFixed(2) + " km";
            document.getElementById('final-time-val').innerText = document.getElementById('time-val').innerText;
            document.getElementById('final-money-val').innerText = Math.round(totalDist * unitPrice).toLocaleString('vi-VN') + " đ";

            // Ẩn màn hình chạy, hiện màn hình thanh toán
            document.getElementById('running-view').style.display = 'none';
            document.getElementById('payment-view').style.display = 'block';
        }}

        // Khi bấm THANH TOÁN -> Làm mới app để quay về màn hình BẮT ĐẦU (Vòng lặp vô hạn)
        function confirmPayment() {{
            window.location.reload();
        }}
    </script>
    </body>
    </html>
    """
  components.html(gps_component_code, height=430)

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
