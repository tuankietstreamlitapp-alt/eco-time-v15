import urllib.parse
import requests
import streamlit as st
from streamlit_js_eval import get_geolocation

st.set_page_config(
    page_title="Đội Xe Ôm Tin Cẩn", page_icon="🛵", layout="centered"
)

st.markdown(
    """
    <div style="text-align: center; background: linear-gradient(135deg, #fff3cd, #ffeeba); padding: 15px; border-radius: 12px; border: 1px solid #ffe8a1;">
        <h2 style="color: #495057; margin-bottom: 5px; font-weight: bold;">🛵 Đội Xe Ôm Tin Cẩn (45–60)</h2>
        <p style="color: #495057; font-size: 15px; font-weight: 500; margin: 0;">Minh bạch - An toàn - Nhanh chóng - Tiện lợi</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# 1. Hàm tìm tọa độ ngầm: Tự động lấy kết quả tốt nhất dựa trên từ khóa người gõ
def lay_toa_do_diem_den(dia_chi):
    if not dia_chi or len(dia_chi.strip()) < 2:
        return None, None

    clean_query = dia_chi.strip()
    if "đồng nai" not in clean_query.lower():
        clean_query += ", Đồng Nai, Việt Nam"

    # Thử tìm bằng Nominatim trước
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(clean_query)}&format=json&countrycodes=vn&limit=1"
        res = requests.get(
            url, headers={"User-Agent": "DoiXeOmApp_Pro/1.0"}, timeout=5
        ).json()
        if res:
            return float(res[0].get("lat")), float(res[0].get("lon"))
    except Exception:
        pass

    # Fallback sang Photon nếu cần
    try:
        url_photon = f"https://photon.komoot.io/api/?q={urllib.parse.quote(clean_query)}&limit=1"
        res_p = requests.get(
            url_photon, headers={"User-Agent": "DoiXeOmApp/1.0"}, timeout=4
        ).json()
        if res_p.get("features"):
            coords = res_p["features"][0]["geometry"]["coordinates"]
            return coords[1], coords[0]
    except Exception:
        pass

    return None, None


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
# BƯỚC 1: 🔍 NHẬP ĐIỂM ĐẾN (TỰ DO, KHÔNG CẦN CHỌN LẠI)
# ==========================================
st.subheader("🏁 Nơi bạn muốn đến")
diem_den_chon = st.text_input(
    "🔍 Nhập tên địa điểm, quán xá, số nhà, tên đường...",
    placeholder="Ví dụ: 9a Nguyễn Khuyến Trảng Dài, Siêu thị BigC...",
)

lat2, lon2 = None, None

if diem_den_chon and len(diem_den_chon.strip()) >= 2:
    with st.spinner("⏳ Đang định vị điểm đến trên bản đồ..."):
        lat2, lon2 = lay_toa_do_diem_den(diem_den_chon)
        if lat2 and lon2:
            st.success("✅ Đã xác định thành công điểm đến!")
        else:
            st.warning(
                "⚠️ Không tìm thấy tọa độ chính xác, app sẽ tính cước tạm tính"
                " hoặc bạn có thể gõ rõ tên đường hơn."
            )

st.divider()

# ==========================================
# BƯỚC 2: 📊 THÔNG TIN CHUYẾN ĐI & CƯỚC PHÍ (ĐÓNG KHUNG KIỂU BILL)
# ==========================================
so_km = 0.0
thoi_gian_phut = 0
lat1, lon1 = None, None
diem_don_text = "Vị trí GPS hiện tại của bạn"

with st.container(border=True):
    st.subheader("🧾 Chi Tiết Cước Phí Chuyến Đi")

    cho_phep_gps = st.radio(
        "📍 Cho phép sử dụng vị trí của bạn?",
        options=["Có (Tự động lấy vị trí đón)", "Không (Tắt định vị)"],
        index=0,
        horizontal=True,
    )

    if cho_phep_gps.startswith("Có"):
        loc = get_geolocation()
        if loc and "coords" in loc:
            lat1 = loc["coords"]["latitude"]
            lon1 = loc["coords"]["longitude"]
            st.success("✅ Đã bật vị trí!")
        else:
            st.info(
                "💡 Trình duyệt đang chờ bạn cấp quyền vị trí. Bấm 'Cho phép' trên"
                " thông báo của trình duyệt."
            )
    else:
        st.warning("⚠️ Bạn đã tắt tính năng định vị vị trí.")

    if lat1 and lon1 and lat2 and lon2:
        km_goc = tinh_so_km_thuc_te(lat1, lon1, lat2, lon2)
        if km_goc:
            so_km = km_goc
            thoi_gian_phut = round((so_km / 30) * 60)
        else:
            so_km = 3.0
            thoi_gian_phut = round((so_km / 30) * 60)

    DONG_GIA = 5000
    gia = so_km * DONG_GIA

    st.markdown("---")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric(label="📏 Quãng đường", value=f"{so_km} Km")
    with col_b:
        st.metric(label="⏱️ Thời gian", value=f"~{thoi_gian_phut} Phút")
    with col_c:
        st.metric(label="💰 Tổng cước", value=f"{gia:,.0f} VNĐ")

st.divider()

# ==========================================
# BƯỚC 3: 📞 KẾT NỐI ĐẶT XE (HOTLINE & ZALO)
# ==========================================
HOTLINE = "0978666620"

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
