import time
import streamlit as st

st.set_page_config(
    page_title="4567 Xe Ôm - Đồng Hồ Minh Bạch", page_icon="🛵", layout="centered"
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
    
    .metric-row {
        font-size: 18px; 
        font-weight: bold; 
        color: #334155; 
        padding: 12px 0; 
        border-bottom: 2px dashed #f1f5f9;
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

# Khởi tạo các biến trạng thái
if "mock_state" not in st.session_state:
    st.session_state.mock_state = "home"
if "start_time" not in st.session_state:
    st.session_state.start_time = 0.0
if "customer_name" not in st.session_state:
    st.session_state.customer_name = ""
if "customer_phone" not in st.session_state:
    st.session_state.customer_phone = ""
if "final_km" not in st.session_state:
    st.session_state.final_km = 0.0
if "final_time" not in st.session_state:
    st.session_state.final_time = "00:00:00"
if "final_money" not in st.session_state:
    st.session_state.final_money = 0

# Cấu hình đơn giá mặc định (5,000 đ/km)
UNIT_PRICE = 5000

# TIÊU ĐỀ APP
st.markdown(
    "<h1 style='text-align:center; color:#059669; margin-bottom:0px;"
    " font-size:28px;'>🛵 4567 XE ÔM</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div style='text-align:center; font-size:15px; color:#64748b;"
    " margin-bottom:12px;'>Tài xế: <b>Nguyễn Văn A</b> &nbsp;|&nbsp; <span"
    " style='color:#10b981;'>● Sẵn sàng</span></div>",
    unsafe_allow_html=True,
)

# KHUNG THẺ CHÍNH
st.markdown("<div class='app-card'>", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# 1. MÀN HÌNH CHỜ (NHẬP KHÁCH & BẮT ĐẦU)
# -------------------------------------------------------------------------
if st.session_state.mock_state == "home":
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
    st.session_state.start_time = (
        time.time()
    )  # Mốc thời gian bắt đầu chính xác từ 0
    st.session_state.mock_state = "running"
    st.rerun()

# -------------------------------------------------------------------------
# 2. MÀN HÌNH ĐANG CHẠY (BẮT ĐẦU TỪ 0 VÀ NHẢY THEO THỜI GIAN THỰC)
# -------------------------------------------------------------------------
elif st.session_state.mock_state == "running":
  st.markdown(
      "<div style='font-size:18px; font-weight:900; color:#059669;"
      " margin-bottom:12px; padding-bottom:8px; border-bottom:2px solid"
      " #f1f5f9; text-align:center;'>⏱️ ĐANG TRONG CUỐC XE...</div>",
      unsafe_allow_html=True,
  )

  # Tính số giây trôi qua thực tế
  elapsed_seconds = int(time.time() - st.session_state.start_time)
  hours = elapsed_seconds // 3600
  minutes = (elapsed_seconds % 3600) // 60
  seconds = elapsed_seconds % 60
  time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

  # Quãng đường tính từ 0 (giả lập tốc độ đô thị ~20km/h)
  current_km = (elapsed_seconds / 3600.0) * 20.0
  current_money = int(current_km * UNIT_PRICE)

  # Hiển thị trực tiếp các thông số bắt đầu từ 0
  st.markdown(
      f"<div class='metric-row'>SỐ KM: <span style='color:#0284c7;"
      f" float:right;'>{current_km:.2f} km</span></div>",
      unsafe_allow_html=True,
  )
  st.markdown(
      f"<div class='metric-row'>THỜI GIAN ĐI: <span style='color:#059669;"
      f" float:right;'>{time_str}</span></div>",
      unsafe_allow_html=True,
  )
  st.markdown(
      f"<div class='metric-row'>ĐƠN GIÁ: <span"
      f" style='float:right;'>{UNIT_PRICE:,} đ/km</span></div>",
      unsafe_allow_html=True,
  )
  st.markdown(
      f"<div class='metric-row' style='font-size:21px; color:#dc2626;"
      f" border-bottom: none;'>THÀNH TIỀN: <span style='float:right;"
      f" font-weight:900;'>{current_money:,} đ</span></div>",
      unsafe_allow_html=True,
  )

  st.write("")
  if st.button(
      "🛑 KẾT THÚC CHUYẾN ĐI", type="primary", use_container_width=True
  ):
    st.session_state.final_km = current_km
    st.session_state.final_time = time_str
    st.session_state.final_money = current_money
    st.session_state.mock_state = "result"
    st.rerun()

  # Cập nhật liên tục mỗi giây
  time.sleep(1)
  st.rerun()

# -------------------------------------------------------------------------
# 3. MÀN HÌNH KẾT QUẢ (CHỐT SỐ LIỆU MINH BẠCH)
# -------------------------------------------------------------------------
elif st.session_state.mock_state == "result":
  st.markdown(
      "<div style='font-size:18px; font-weight:900; color:#059669;"
      " margin-bottom:12px; padding-bottom:8px; border-bottom:2px solid"
      " #f1f5f9; text-align:center;'>📋 KẾT QUẢ CUỐC ĐI</div>",
      unsafe_allow_html=True,
  )

  if st.session_state.customer_name:
    st.markdown(
        f"<div style='font-size:15px; color:#334155; margin-bottom:8px;'>Khách:"
        f" <b>{st.session_state.customer_name}</b> ({st.session_state.customer_phone})</div>",
        unsafe_allow_html=True,
    )

  st.markdown(
      f"<div class='metric-row'>SỐ KM: <span style='color:#0284c7;"
      f" float:right;'>{st.session_state.final_km:.2f} km</span></div>",
      unsafe_allow_html=True,
  )
  st.markdown(
      f"<div class='metric-row'>THỜI GIAN ĐI: <span style='color:#059669;"
      f" float:right;'>{st.session_state.final_time}</span></div>",
      unsafe_allow_html=True,
  )
  st.markdown(
      f"<div class='metric-row'>ĐƠN GIÁ: <span"
      f" style='float:right;'>{UNIT_PRICE:,} đ/km</span></div>",
      unsafe_allow_html=True,
  )
  st.markdown(
      f"<div class='metric-row' style='font-size:21px; color:#059669;"
      f" border-bottom: none;'>THÀNH TIỀN: <span style='float:right;"
      f" font-weight:900;'>{st.session_state.final_money:,} đ</span></div>",
      unsafe_allow_html=True,
  )

  st.write("")
  if st.button("♻️ NHẬN CUỐC XE MỚI", type="primary", use_container_width=True):
    st.session_state.mock_state = "home"
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

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
