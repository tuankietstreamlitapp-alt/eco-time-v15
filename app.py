import streamlit as st

st.set_page_config(
    page_title="4567 Xe Ôm - Giao Diện", page_icon="🛵", layout="centered"
)

# ============================================================
# CSS TỐI ƯU GIAO DIỆN KHÔNG BỊ CẮT CHỮ, THOÁNG ĐÃNG, TO RÕ
# ============================================================
st.markdown(
    """
    <style>
    .stApp { background-color: #f1f5f9; }
    
    /* Khắc phục triệt để lỗi bị cắt chữ ở trên cùng */
    .block-container { 
        max-width: 500px; 
        padding-top: 1rem !important; 
        padding-bottom: 2rem; 
        padding-left: 1rem; 
        padding-right: 1rem; 
    }
    
    /* Ẩn bớt các thành phần mặc định thừa của Streamlit nếu cần để thoáng màn hình */
    header { visibility: hidden; }
    
    /* Nút bấm siêu to khổng lồ cho bác tài dễ bấm */
    div.stButton > button { 
        border-radius: 14px !important; 
        font-weight: 900 !important; 
        font-size: 22px !important; 
        min-height: 60px !important; 
    }
    
    /* Khung thẻ nội dung */
    .app-card { 
        background: #ffffff; 
        border-radius: 18px; 
        padding: 20px; 
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.04); 
        margin-top: 10px; 
        margin-bottom: 15px; 
        border: 1px solid #e2e8f0; 
    }
    
    /* Dòng thông số */
    .metric-row {
        font-size: 18px; 
        font-weight: bold; 
        color: #334155; 
        padding: 12px 0; 
        border-bottom: 2px dashed #f1f5f9;
    }
    
    /* Nút Zalo liên hệ độc lập ở đáy */
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

# Quản lý trạng thái giao diện mẫu
if "mock_state" not in st.session_state:
    st.session_state.mock_state = "home"

# TIÊU ĐỀ APP (Đã hạ xuống thấp, không bị thanh công cụ che khuất)
st.markdown("<h1 style='text-align:center; color:#059669; margin-bottom:0px; font-size:28px;'>🛵 4567 XE ÔM</h1>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center; font-size:15px; color:#64748b; margin-bottom:12px;'>Tài xế: <b>Nguyễn Văn A</b> &nbsp;|&nbsp; <span style='color:#10b981;'>● Sẵn sàng</span></div>", unsafe_allow_html=True)

# MỞ KHUNG THẺ CHÍNH (Đã bỏ thanh màu tránh rườm rà phía trên)
st.markdown("<div class='app-card'>", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# 1. MÀN HÌNH CHỜ (NHẬP KHÁCH & BẮT ĐẦU)
# -------------------------------------------------------------------------
if st.session_state.mock_state == "home":
    st.markdown("<div style='font-weight:bold; font-size:16px; color:#1e293b; margin-bottom:10px;'>📍 THÔNG TIN KHÁCH HÀNG</div>", unsafe_allow_html=True)
    st.text_input("TÊN KHÁCH HÀNG:", placeholder="Bỏ trống nếu khách vãng lai")
    st.text_input("SỐ ĐIỆN THOẠI:", placeholder="Nhập SĐT khách hàng...")

    st.write("")
    if st.button("🟢 BẮT ĐẦU CHẠY", type="primary", use_container_width=True):
        st.session_state.mock_state = "running"
        st.rerun()

# -------------------------------------------------------------------------
# 2. MÀN HÌNH ĐANG CHẠY (HIỂN THỊ 4 THÔNG SỐ)
# -------------------------------------------------------------------------
elif st.session_state.mock_state == "running":
    st.markdown("<div style='text-align:center; color:#059669; font-weight:bold; font-size:17px; margin-bottom:10px;'>⏱️ ĐANG TRONG CUỐC XE...</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='metric-row'>SỐ KM: <span style='color:#0284c7; float:right;'>3.45 km</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-row'>THỜI GIAN ĐI: <span style='color:#059669; float:right;'>00:15:20</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-row'>ĐƠN GIÁ: <span style='float:right;'>5,000 đ/km</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-row' style='font-size:21px; color:#dc2626; border-bottom: none;'>THÀNH TIỀN: <span style='float:right; font-weight:900;'>17,250 đ</span></div>", unsafe_allow_html=True)
    
    st.write("")
    if st.button("🛑 KẾT THÚC CHUYẾN ĐI", type="primary", use_container_width=True):
        st.session_state.mock_state = "result"
        st.rerun()

# -------------------------------------------------------------------------
# 3. MÀN HÌNH KẾT QUẢ
# -------------------------------------------------------------------------
elif st.session_state.mock_state == "result":
    st.markdown("<div style='font-weight:bold; font-size:16px; color:#1e293b; margin-bottom:10px;'>📋 KẾT QUẢ CUỐC ĐI</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='metric-row'>SỐ KM: <span style='color:#0284c7; float:right;'>3.45 km</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-row'>THỜI GIAN ĐI: <span style='color:#059669; float:right;'>00:15:20</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-row'>ĐƠN GIÁ: <span style='float:right;'>5,000 đ/km</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-row' style='font-size:21px; color:#059669; border-bottom: none;'>THÀNH TIỀN: <span style='float:right; font-weight:900;'>17,250 đ</span></div>", unsafe_allow_html=True)
    
    st.write("")
    if st.button("♻️ NHẬN CUỐC XE MỚI", type="primary", use_container_width=True):
        st.session_state.mock_state = "home"
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# KHU VỰC HỖ TRỢ (GỘP THÀNH 1 NÚT ZALO DUY NHẤT Ở ĐÁY)
# ============================================================
st.markdown("<div style='margin-top: 15px;'>", unsafe_allow_html=True)
st.markdown('<a href="https://zalo.me/0978666620" class="btn-zalo-single" target="_blank">💬 LIÊN HỆ HỖ TRỢ ZALO</a>', unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)
