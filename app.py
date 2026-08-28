import streamlit as st

st.set_page_config(page_title="Đội Xe Ôm Tin Cẩn", page_icon="🛵")

st.title("🛵 Đội Xe Ôm Tin Cẩn (45–60)")
st.write("Minh bạch - An toàn - Không lo chặt chém")

st.divider()

# Khách nhập thông tin
diem_don = st.text_input("📍 Điểm đón:", placeholder="Ví dụ: 123 Nguyễn Văn Cừ")
diem_den = st.text_input("🏁 Điểm đến:", placeholder="Ví dụ: Chợ Long Xuyên")

so_km = st.number_input("📏 Nhập số km ước tính (hoặc theo Google Maps):", min_value=0.5, value=2.0, step=0.5)

# Thuật toán tính giá minh bạch
if so_km <= 2:
    gia = 15000
else:
    gia = 15000 + (so_km - 2) * 5000

st.metric(label="💰 Tổng cước phí dự kiến", value=f"{gia:,.0f} VNĐ")

# Nút bấm gọi xe
if st.button("📞 GỌI XUẤT XE NGAY", use_container_width=True, type="primary"):
    st.success(f"Dịch vụ đang điều xe đón bạn tại: **{diem_don}**!")
    st.info("Vui lòng liên hệ Hotline/Zalo: **090x xxx xxx** để xác nhận chuyến.")
