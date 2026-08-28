import urllib.parse
import streamlit as st

st.set_page_config(
    page_title="Đội Xe Ôm Tin Cẩn", page_icon="🛵", layout="centered"
)

st.title("🛵 Đội Xe Ôm Tin Cẩn (45–60)")
st.caption("Minh bạch - An toàn - Không lo chặt chém")

st.divider()

# 1. Khách nhập thông tin
diem_don = st.text_input(
    "📍 Điểm đón của bạn:", placeholder="Ví dụ: 123 Nguyễn Văn Cừ"
)
diem_den = st.text_input(
    "🏁 Điểm đến:", placeholder="Ví dụ: Mitsubishi Motors Đồng Nai"
)

so_km = st.number_input(
    "📏 Nhập số km ước tính (theo Google Maps):",
    min_value=0.5,
    value=6.0,
    step=0.5,
    format="%.1f",
)

# 2. Thuật toán tính giá minh bạch
if so_km <= 2:
    gia = 15000
else:
    gia = 15000 + (so_km - 2) * 5000

st.metric(label="💰 Tổng cước phí dự kiến", value=f"{gia:,.0f} VNĐ")

st.divider()

# 3. Xử lý xuất lộ trình và nút kết nối
HOTLINE = "0901234567"  # Ní thay số điện thoại hotline của ní/đội vào đây

if diem_don and diem_den:
    # Tạo link Google Maps tự động cho tài xế
    don_encoded = urllib.parse.quote(diem_don)
    den_encoded = urllib.parse.quote(diem_den)
    maps_url = f"https://www.google.com/maps/dir/?api=1&origin={don_encoded}&destination={den_encoded}&travelmode=driving"

    st.markdown(
        f"🧭 **Lộ trình cho tài xế:** [Mở chỉ đường Google Maps]({maps_url})"
    )

    # Nội dung tin nhắn Zalo tự động
    noi_dung_zalo = urllib.parse.quote(
        f"Chào Đội Xe, tôi muốn đặt xe:\n- Đón: {diem_don}\n- Đến: {diem_den}\n- Quãng đường: {so_km}km\n- Cước phí: {gia:,.0f}đ"
    )
    zalo_url = f"https://zalo.me/{HOTLINE}?text={noi_dung_zalo}"

    # Nút bấm thao tác nhanh
    col1, col2 = st.columns(2)
    with col1:
        st.link_button(
            "📞 GỌI TỔNG ĐÀI",
            f"tel:{HOTLINE}",
            use_container_width=True,
            type="primary",
        )
    with col2:
        st.link_button(
            "💬 NHẮN ZALO ĐẶT XE", zalo_url, use_container_width=True
        )
else:
    st.info("💡 Ní vui lòng điền đủ Điểm đón và Điểm đến để kích hoạt đặt xe.")
