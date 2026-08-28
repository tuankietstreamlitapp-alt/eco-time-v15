import urllib.parse
import requests
import streamlit as st
from geopy.geocoders import Nominatim

st.set_page_config(
    page_title="Đội Xe Ôm Tin Cẩn", page_icon="🛵", layout="centered"
)

st.title("🛵 Đội Xe Ôm Tin Cẩn (45–60)")
st.caption("Minh bạch - An toàn - Tự động tính cước chuẩn xác")

st.divider()


# Hàm tính số km lái xe thực tế giữa 2 địa điểm
def tinh_so_km_thuc_te(dia_chi_don, dia_chi_den):
    try:
        geolocator = Nominatim(user_agent="doi_xe_om_app")

        # Lấy tọa độ điểm đón
        loc1 = geolocator.geocode(f"{dia_chi_don}, Việt Nam")
        # Lấy tọa độ điểm đến
        loc2 = geolocator.geocode(f"{dia_chi_den}, Việt Nam")

        if loc1 and loc2:
            # Gọi API OSRM đo quãng đường lái xe thực tế
            url = f"http://router.project-osrm.org/route/v1/driving/{loc1.longitude},{loc1.latitude};{loc2.longitude},{loc2.latitude}?overview=false"
            res = requests.get(url, timeout=5).json()

            if "routes" in res and len(res["routes"]) > 0:
                met = res["routes"][0]["distance"]
                km = met / 1000.0
                return round(km, 2)
    except Exception:
        pass
    return None


# 1. Nhập điểm đón & điểm đến
col_don, col_den = st.columns(2)

with col_don:
    diem_don = st.text_input(
        "📍 Điểm đón của bạn:",
        value="Vị trí hiện tại",
        placeholder="Nhập địa chỉ đón...",
    )

with col_den:
    diem_den = st.text_input(
        "🏁 Điểm đến:", placeholder="Ví dụ: Chợ Long Xuyên / Bệnh viện..."
    )

so_km = 0.0
gia = 0

# 2. Tự động tính toán khi có đủ 2 điểm
if diem_don and diem_den and diem_don != "Vị trí hiện tại":
    with st.spinner("⏳ Đang đo quãng đường thực tế trên bản đồ..."):
        km_co_dinh = tinh_so_km_thuc_te(diem_don, diem_den)

        if km_co_dinh:
            so_km = km_co_dinh
            st.success(
                f"📏 Quãng đường lái xe thực tế trên bản đồ: **{so_km} km**"
            )
        else:
            st.warning(
                "⚠️ Không tìm thấy tọa độ chính xác, vui lòng nhập số km ước tính bên dưới:"
            )
            so_km = st.number_input("📏 Nhập km thủ công:", min_value=0.5, value=5.0, step=0.5)
else:
    if diem_den:
        so_km = st.number_input(
            "📏 Quãng đường ước tính (km):", min_value=0.5, value=5.0, step=0.5
        )

# 3. Tính cước phí theo công thức: Số km * 2.000 VNĐ
DONG_GIA = 2000
gia = so_km * DONG_GIA

st.metric(
    label="💰 Tổng cước phí dự kiến (2.000đ/km)", value=f"{gia:,.0f} VNĐ"
)

st.divider()

# 4. Nút bấm kết nối Hotline & Zalo
HOTLINE = "0901234567"  # Ní thay SĐT hotline vào đây

if diem_den:
    don_encoded = urllib.parse.quote(diem_don)
    den_encoded = urllib.parse.quote(diem_den)
    maps_url = f"https://www.google.com/maps/dir/?api=1&origin={don_encoded}&destination={den_encoded}&travelmode=driving"

    st.markdown(
        f"🧭 **Lộ trình trực tuyến trên Google Maps:** [Bấm để xem chỉ đường]({maps_url})"
    )

    noi_dung_zalo = urllib.parse.quote(
        f"Chào Đội Xe, tôi muốn đặt xe:\n- Đón: {diem_don}\n- Đến: {diem_den}\n- Quãng đường: {so_km}km\n- Cước phí dự kiến: {gia:,.0f}đ"
    )
    zalo_url = f"https://zalo.me/{HOTLINE}?text={noi_dung_zalo}"

    c1, c2 = st.columns(2)
    with c1:
        st.link_button(
            "📞 GỌI XUẤT XE NGAY",
            f"tel:{HOTLINE}",
            use_container_width=True,
            type="primary",
        )
    with c2:
        st.link_button(
            "💬 GỬI ĐƠN QUA ZALO", zalo_url, use_container_width=True
        )
