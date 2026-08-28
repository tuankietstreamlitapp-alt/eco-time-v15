import urllib.parse
import requests
import streamlit as st
from streamlit_js_eval import get_geolocation

st.set_page_config(
    page_title="Đội Xe Ôm Tin Cẩn", page_icon="🛵", layout="centered"
)

st.title("🛵 Đội Xe Ôm Tin Cẩn (45–60)")
st.caption("Minh bạch - An toàn - Nhanh chóng - Tiện lợi")

st.divider()


# 1. Hàm tìm danh sách địa điểm gợi ý
def lay_danh_sach_goi_y(dia_chi):
    if not dia_chi or len(dia_chi.strip()) < 2:
        return []
    dia_chi_sach = dia_chi.replace("-", " ").strip()
    danh_sach = []
    try:
        url = f"https://photon.komoot.io/api/?q={urllib.parse.quote(dia_chi_sach + ' Đồng Nai Việt Nam')}&limit=5"
        res = requests.get(
            url, headers={"User-Agent": "DoiXeOmApp/1.0"}, timeout=4
        ).json()
        if res.get("features"):
            for item in res["features"]:
                props = item.get("properties", {})
                name = props.get("name", "")
                street = props.get("street", "")
                district = props.get("district", props.get("county", ""))
                city = props.get("city", "")
                chi_tiet = ", ".join(
                    filter(None, [name, street, district, city])
                )
                if not chi_tiet:
                    chi_tiet = dia_chi_sach
                coords = item["geometry"]["coordinates"]
                danh_sach.append(
                    {"label": chi_tiet, "lat": coords[1], "lon": coords[0]}
                )
    except Exception:
        pass
    return danh_sach


# 2. Hàm tính km chuẩn xác sát thực tế (Khớp Google Maps)
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


# ==========================================
# BƯỚC 1: 🔍 NHẬP ĐIỂM ĐẾN (ƯU TIÊN HÀNG ĐẦU)
# ==========================================
st.subheader("🏁 Nơi bạn muốn đến")
tim_kiem_den = st.text_input(
    "🔍 Nhập tên địa điểm, quán xá, bệnh viện...",
    placeholder="Ví dụ: Xe Máy Quốc Sự, Siêu thị BigC...",
)

lat2, lon2 = None, None
diem_den_chon = ""

if tim_kiem_den:
    with st.spinner("⏳ Đang tìm kiếm các địa điểm phù hợp..."):
        ds_goc = lay_danh_sach_goi_y(tim_kiem_den)

    if ds_goc:
        lua_chon_labels = [item["label"] for item in ds_goc]
        chon_diem = st.selectbox(
            "🎯 Chọn chính xác kết quả đúng nhất trong danh sách:",
            lua_chon_labels,
        )
        for item in ds_goc:
            if item["label"] == chon_diem:
                lat2, lon2 = item["lat"], item["lon"]
                diem_den_chon = item["label"]
                break
    else:
        st.warning(
            "⚠️ Không tìm thấy địa điểm, vui lòng gõ rõ hơn tên đường hoặc khu vực."
        )

st.divider()

# ==========================================
# BƯỚC 2: 📊 HIỂN THỊ KẾT QUẢ KHOẢNG CÁCH & CƯỚC PHÍ
# ==========================================
st.subheader("📊 Thông tin chuyến đi & Cước phí")

so_km = 0.0
thoi_gian_phut = 0
lat1, lon1 = None, None
diem_don_text = "Vị trí GPS hiện tại của bạn"

# Lựa chọn cấp quyền sử dụng vị trí (Có / Không)
cho_phep_gps = st.radio(
    "📍 Tự động lấy vị trí đón.",
    options=["Cho phép.", "Không cho phép."],
    index=0,
    horizontal=True,
)

if cho_phep_gps.startswith("Có"):
    loc = get_geolocation()
    if loc and "coords" in loc:
        lat1 = loc["coords"]["latitude"]
        lon1 = loc["coords"]["longitude"]
        st.success("✅ Đã vị trí đón thành công!")
    else:
        st.info(
            "💡 Trình duyệt đang chờ bạn cấp quyền vị trí. Bấm 'Cho phép' trên"
            " bảng thông báo của trình duyệt nếu có."
        )
else:
    st.warning("⚠️ Bạn đã tắt tính năng vị trí.")

if lat1 and lon1 and lat2 and lon2:
    km_goc = tinh_so_km_thuc_te(lat1, lon1, lat2, lon2)
    if km_goc:
        so_km = km_goc
        thoi_gian_phut = round((so_km / 30) * 60)
    else:
        so_km = 3.0
        thoi_gian_phut = round((so_km / 30) * 60)

# Đơn giá cố định 5k/km
DONG_GIA = 5000
gia = so_km * DONG_GIA

# Hiển thị trực quan các ô thông tin ngang hàng
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.metric(label="📏 Quãng đường", value=f"{so_km} km")
with col_b:
    st.metric(label="⏱️ Thời gian", value=f"~{thoi_gian_phut} phút")
with col_c:
    st.metric(label="💰 Tổng cước phí", value=f"{gia:,.0f} đ")

st.divider()

# ==========================================
# BƯỚC 3: 📞 KẾT NỐI ĐẶT XE (HOTLINE & ZALO)
# ==========================================
HOTLINE = "0978666620"  # Ní thay SĐT của chú bác tài xế vào đây

if diem_den_chon and lat1 and lon1 and so_km > 0:
    maps_url = f"https://www.google.com/maps/dir/?api=1&origin={lat1},{lon1}&destination={urllib.parse.quote(diem_den_chon)}&travelmode=driving"

    st.markdown(
        f"🧭 **Bản đồ chỉ đường cho Tài Xế:** [Bấm để mở Google Maps]({maps_url})"
    )

    noi_dung_zalo = urllib.parse.quote(
        f"Chào Đội Xe, tôi muốn đặt xe:\n- Đón: {diem_don_text}\n- Đến: {diem_den_chon}\n- Quãng đường: {so_km}km (~{thoi_gian_phut} phút)\n- Cước phí: {gia:,.0f}đ"
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
else:
    st.info(
        "💡 Vui lòng nhập điểm đến và bật cho phép sử dụng vị trí để hiển thị nút"
        " đặt xe."
    )
