import streamlit as st

st.set_page_config(
    page_title="4567 Xe Ôm - Giao Diện Mẫu", page_icon="🛵", layout="centered"
)

# ============================================================
# CSS GIAO DIỆN TỐI GIẢN - FONT TO, DỄ NHÌN CHO NGƯỜI LỚN TUỔI
# ============================================================
st.markdown(
    """
    <style>
    .stApp { background-color: #f1f5f9; }
    .block-container { max-width: 500px; padding: 1.5rem 1rem; }
    
    /* Nút bấm siêu to khổng lồ */
    div.stButton > button { 
        border-radius: 14px !important; 
        font-weight: 900 !important; 
        font-size: 24px !important; 
        min-height: 65px !important; 
    }
    
    /* Khung thẻ bao bọc nội dung */
    .app-card { 
        background: #ffffff; border-radius: 18px; padding: 22px; 
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05); 
        margin-bottom: 20px; border: 2px solid #e2e8f0; 
    }
    
    /* Dòng hiển thị thông số */
    .metric-row {
        font-size: 19px; font-weight: bold; color: #334155; 
        padding: 12px 0; border-bottom: 2px dashed #cbd5e1;
    }
    
    .btn-sos { background: #ef4444; color: white; padding: 14px; border-radius: 12px; text-align: center; font-weight: bold; font-size: 16px; display: block; text-decoration: none;}
    .btn-zalo { background: #0284c7; color: white; padding: 14px; border-radius: 12px; text-align: center; font-weight: bold; font-size: 16px; display: block; text-decoration: none;}
    </style>
    """,
    unsafe_allow_html=True,
)

# Quản lý trạng thái giao diện mẫu (Chưa dính database)
if "mock_state" not in st.session_state:
    st.session_state.mock_state = "home" # home (chờ khách) -> running (đang chạy) -> result (kết quả)

# Tiêu đề App
st.markdown("<h2 style='text-align:center; color:#059669; margin-bottom:5px;'>🛵 4567 XE ÔM</h2>", unsafe_allow_html=True)
st.markdown("<div style='text-align:center; font-size:15px; color:#64748b; margin-bottom:15px;'>Tài xế: <b>Nguyễn Văn A</b> | 🟢 Sẵn sàng</div>", unsafe_allow_html=True)

st.markdown("<div class='app-card'>", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# TRẠNG THÁI 1: MÀN HÌNH CHỜ (NHẬP KHÁCH & BẤM BẮT ĐẦU)
# -------------------------------------------------------------------------
if st.session_state.mock_state == "home":
    st.markdown("<h4 style='color:#1e293b; margin-top:0;'>📍 THÔNG TIN KHÁCH HÀNG</h4>", unsafe_allow_html=True)
    st.text_input("TÊN KHÁCH HÀNG:", placeholder="Bỏ trống nếu khách vãng lai")
    st.text_input("SỐ ĐIỆN THOẠI:", placeholder="Nhập SĐT khách hàng...")

    st.write("")
    if st.button("🟢 BẮT ĐẦU CHẠY", type="primary", use_container_width=True):
        st.session_state.mock_state = "running"
        st.rerun()

# -------------------------------------------------------------------------
# TRẠNG THÁI 2: MÀN HÌNH ĐANG CHẠY (HIỂN THỊ 4 THÔNG SỐ + NÚT KẾT THÚC)
# -------------------------------------------------------------------------
elif st.session_state.mock_state == "running":
    st.markdown("<div style='text-align:center; color:#059669; font-weight:bold; font-size:18px; margin-bottom:10px;'>⏱️ ĐANG TRONG CUỐC XE...</div>", unsafe_allow_html=True)
    
    st.markdown("<div class='metric-row'>SỐ KM: <span style='color:#0284c7; float:right;'>3.45 km</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-row'>THỜI GIAN ĐI: <span style='color:#059669; float:right;'>00:15:20</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-row'>ĐƠN GIÁ: <span style='float:right;'>5,000 đ/km</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-row' style='font-size:22px; color:#dc2626; border-bottom: 2px solid #0f172a;'>THÀNH TIỀN: <span style='float:right; font-weight:900;'>17,250 đ</span></div>", unsafe_allow_html=True)
    
    st.write("")
    if st.button("🛑 KẾT THÚC CHUYẾN ĐI", type="primary", use_container_width=True):
        st.session_state.mock_state = "result"
        st.rerun()

# -------------------------------------------------------------------------
# TRẠNG THÁI 3: MÀN HÌNH KẾT QUẢ (XEM LẠI ĐƠN GIẢN, KHÔNG POPUP)
# -------------------------------------------------------------------------
elif st.session_state.mock_state == "result":
    st.markdown("<h4 style='text-align:center; color:#1e293b; margin-top:0;'>📋 KẾT QUẢ CUỐC ĐI</h4>", unsafe_allow_html=True)
    
    st.markdown("<div class='metric-row'>SỐ KM: <span style='color:#0284c7; float:right;'>3.45 km</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-row'>THỜI GIAN ĐI: <span style='color:#059669; float:right;'>00:15:20</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-row'>ĐƠN GIÁ: <span style='float:right;'>5,000 đ/km</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-row' style='font-size:22px; color:#059669; border-bottom: 2px solid #0f172a;'>THÀNH TIỀN: <span style='float:right; font-weight:900;'>17,250 đ</span></div>", unsafe_allow_html=True)
    
    st.write("")
    if st.button("♻️ NHẬN CUỐC XE MỚI", type="primary", use_container_width=True):
        st.session_state.mock_state = "home"
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# KHU VỰC HỖ TRỢ ĐÁY APP
# ============================================================
st.write("---")
c1, c2 = st.columns(2)
with c1:
    st.markdown('<a href="#" class="btn-sos">🚨 GỌI SOS</a>', unsafe_allow_html=True)
with c2:
    st.markdown('<a href="#" class="btn-zalo">💬 ZALO ADMIN</a>', unsafe_allow_html=True)
