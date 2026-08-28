import urllib.parse
import requests
import streamlit as st
from streamlit_js_eval import get_geolocation

st.set_page_config(
    page_title="Đội Xe Ôm Tin Cẩn", page_icon="🛵", layout="centered"
)

st.title("🛵 Đội Xe Ôm Tin Cẩn (45–60)")
st.caption("Minh bạch - An toàn - Tự động định vị GPS thực tế")

st.divider()


# 1. Hàm định vị địa danh nếu khách tự gõ bằng tay
def lay_toa_do_tu_ten(dia_chi):
    if not dia_chi or dia_chi.strip() == "":
        return None, None
    dia_chi_sach = dia_chi.replace("-", " ").strip()
    try:
        url = f"https://photon.komoot.io/api/?q={urllib.parse.quote(dia_chi_sach + ' Đồng Nai Việt Nam')}&limit=1"
        res = requests.get(
            url, headers={"User-Agent": "DoiXeOmApp/1.0"}, timeout=4
        ).json()
        if res.get("features") and len(res["features"]) > 0:
            coords = res["features"][0]["geometry"]["coordinates"]
            return coords[1], coords[0]  # (lat, lon)
    except Exception:
        pass
    return None, None


# 2. Hàm tính km lái xe thực tế
def tinh_so_km_thuc_te(lat1, lon1, lat2, lon2):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        res = requests.get(url, timeout=5).json()
        if "routes" in res and len(res["routes"]) > 0:
            met = res["routes"][0]["distance"]
            return round(met / 1000.0, 2)
    except Exception:
        pass
    return None


# 3. LẤY TỌA ĐỘ GPS THỰC TẾ TỪ ĐIỆN THOẠI KHÁCH
st.subheader("1. Vị trí đón của bạn")
dung_gps = st.checkbox("📍 Tự động lấy Vị trí GPS hiện tại của tôi", value=True)

lat1, lon1 = None, None
diem_don_text = ""

if dung_gps:
    loc = get_geolocation()
    if loc and "coords" in loc:
        lat1 = loc["coords"]["latitude"]
        lon1 = loc["coords"]["longitude"]
        diem_don_text = "Vị trí GPS hiện tại của bạn"
        st.success(
            f"🎯 Đã xác định GPS chính xác của điện thoại! ({lat1:.4f}, {lon1:.4f})"
        )
    else:
        st.info("💡 Vui lòng bấm 'Cho phép' khi trình duyệt hỏi quyền truy cập Vị trí/GPS.")
        diem_don_input = st.text_input(
            "Hoặc nhập Điểm đón thủ công:",
            placeholder="Ví dụ: Công ty Taekwang Vina...",
        )
        if diem_don_input:
            lat1, lon1 = lay_toa_do_tu_ten(diem_don_input)
            diem_don_text = diem_don_input
else:
    diem_don_input = st.text_input(
        "Nhập Điểm đón thủ công:", placeholder="Ví dụ: Ngã tư AMATA..."
    )
    if diem_don_input:
        lat1, lon1 = lay_toa_do_tu_ten(diem_don_input)
        diem_don_text = diem_don_input

st.divider()

# 4. NHẬP ĐIỂM ĐẾN
st.subheader("2. Nơi bạn muốn đến")
diem_den = st.text_input(
    "🏁 Điểm đến:", placeholder="Ví dụ: Nhà Thờ Giáo Xứ Bùi Đệ..."
)

so_km = 0.0

# 5. TÍNH KHOẢNG CÁCH VÀ CƯỚC PHÍ
if lat1 and lon1 and diem_den:
    lat2, lon2 = lay_toa_do_tu_ten(diem_den)

    if lat2 and lon2:
        km = tinh_so_km_thuc_te(lat1, lon1, lat2, lon2)
        if km:
            so_km = km
            st.success(
                f"✅ Quãng đường thực tế trên Google Maps: **{so_km} km**"
            )
        else:
            st.warning("⚠️ Không tìm thấy tuyến đường lái xe, vui lòng nhập km thủ công:")
            so_km = st.number_input("📏 Nhập km thủ công:", min_value=0.5, value=5.0, step=0.5)
    else:
        st.warning("⚠️ Không tìm thấy vị trí điểm đến, vui lòng kiểm tra lại tên điểm đến.")

# Tính cước phí đồng giá 2.000 VNĐ/km
DONG_GIA = 2000
gia = so_km * DONG_GIA

st.metric(
    label="💰 Tổng cước phí dự kiến (2.000đ/km)", value=f"{gia:,.0f} VNĐ"
)

st.divider()

# 6. ĐẶT XE
HOTLINE = "0901234567"  # Ní thay SĐT hotline vào đây

if diem_den and lat1 and lon1:
    maps_url = f"https://www.google.com/maps/dir/?api=1&origin={lat1},{lon1}&destination={urllib.parse.quote(diem_den)}&travelmode=driving"

    st.markdown(
        f"🧭 **Lộ trình trực tuyến cho Tài Xế:** [Bấm để mở Google Maps]({maps_url})"
    )

    noi_dung_zalo = urllib.parse.quote(
        f"Chào Đội Xe, tôi muốn đặt xe:\n- Đón: {diem_don_text}\n- Đến: {diem_den}\n- Quãng đường: {so_km}km\n- Cước phí: {gia:,.0f}đ"
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
