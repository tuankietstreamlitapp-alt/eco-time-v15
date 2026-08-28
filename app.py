import urllib.parse
import requests
import streamlit as st

st.set_page_config(
    page_title="Đội Xe Ôm Tin Cẩn", page_icon="🛵", layout="centered"
)

st.title("🛵 Đội Xe Ôm Tin Cẩn (45–60)")
st.caption("Minh bạch - An toàn - Tự động tính cước chuẩn xác")

st.divider()


# 1. Hàm lấy tọa độ thông minh (Photon API - Fuzzy Search cực mạnh cho địa danh VN)
def lay_toa_do_thong_minh(dia_chi):
    if not dia_chi or dia_chi.strip() == "":
        return None, None

    # Làm sạch chuỗi tìm kiếm
    dia_chi_sach = dia_chi.replace("-", " ").strip()

    # Thử tìm kiếm với Photon API
    try:
        url = f"https://photon.komoot.io/api/?q={urllib.parse.quote(dia_chi_sach)}&limit=1"
        res = requests.get(
            url, headers={"User-Agent": "DoiXeOmApp/1.0"}, timeout=4
        ).json()
        if res.get("features") and len(res["features"]) > 0:
            coords = res["features"][0]["geometry"]["coordinates"]
            return coords[1], coords[0]  # Tra ve (lat, lon)
    except Exception:
        pass

    # Nếu chưa tìm thấy, thử thêm chữ "Việt Nam" để định vị chuẩn hơn
    try:
        url_vn = f"https://photon.komoot.io/api/?q={urllib.parse.quote(dia_chi_sach + ' Việt Nam')}&limit=1"
        res_vn = requests.get(
            url_vn, headers={"User-Agent": "DoiXeOmApp/1.0"}, timeout=4
        ).json()
        if res_vn.get("features") and len(res_vn["features"]) > 0:
            coords = res_vn["features"][0]["geometry"]["coordinates"]
            return coords[1], coords[0]
    except Exception:
        pass

    return None, None


# 2. Hàm tính khoảng cách lái xe thực tế (OSRM Routing)
def tinh_so_km_thuc_te(don_lat, don_lon, den_lat, den_lon):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{don_lon},{don_lat};{den_lon},{den_lat}?overview=false"
        res = requests.get(url, timeout=5).json()
        if "routes" in res and len(res["routes"]) > 0:
            met = res["routes"][0]["distance"]
            return round(met / 1000.0, 2)
    except Exception:
        pass
    return None


# 3. Giao diện nhập liệu
col_don, col_den = st.columns(2)

with col_don:
    diem_don = st.text_input(
        "📍 Điểm đón của bạn:",
        placeholder="Ví dụ: Công Ty Taekwang Vina Long Bình...",
    )

with col_den:
    diem_den = st.text_input(
        "🏁 Điểm đến:", placeholder="Ví dụ: Nhà Thờ Giáo Xứ Bùi Đệ..."
    )

so_km = 0.0

# 4. Xử lý tính quãng đường & cước phí
if diem_don and diem_den:
    with st.spinner("⏳ Đang định vị địa danh & đo quãng đường thực tế..."):
        lat1, lon1 = lay_toa_do_thong_minh(diem_don)
        lat2, lon2 = lay_toa_do_thong_minh(diem_den)

        if lat1 and lat2:
            km_lay_duoc = tinh_so_km_thuc_te(lat1, lon1, lat2, lon2)
            if km_lay_duoc:
                so_km = km_lay_duoc
                st.success(
                    f"✅ Đã tìm thấy vị trí! Quãng đường thực tế: **{so_km} km**"
                )
            else:
                st.warning("⚠️ Không tính được tuyến đường lái xe, vui lòng nhập km thủ công:")
                so_km = st.number_input("📏 Nhập km thủ công:", min_value=0.5, value=5.0, step=0.5)
        else:
            st.warning("⚠️ Không tìm thấy tọa độ chính xác, vui lòng nhập số km ước tính bên dưới:")
            so_km = st.number_input("📏 Nhập km thủ công:", min_value=0.5, value=5.0, step=0.5)

# Tính cước đồng giá 2.000 VNĐ/km
DONG_GIA = 2000
gia = so_km * DONG_GIA

st.metric(
    label="💰 Tổng cước phí dự kiến (2.000đ/km)", value=f"{gia:,.0f} VNĐ"
)

st.divider()

# 5. Nút bấm đặt xe & Google Maps
HOTLINE = "0901234567"  # Ní thay SĐT hotline thực tế vào đây

if diem_den:
    don_encoded = urllib.parse.quote(diem_don)
    den_encoded = urllib.parse.quote(diem_den)
    maps_url = f"https://www.google.com/maps/dir/?api=1&origin={don_encoded}&destination={den_encoded}&travelmode=driving"

    st.markdown(
        f"🧭 **Lộ trình trực tuyến trên Google Maps:** [Bấm để xem chỉ đường]({maps_url})"
    )

    noi_dung_zalo = urllib.parse.quote(
        f"Chào Đội Xe, tôi muốn đặt xe:\n- Đón: {diem_don}\n- Đến: {diem_den}\n- Quãng đường: {so_km}km\n- Cước phí: {gia:,.0f}đ"
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
