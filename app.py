import re
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


# 1. Tìm tọa độ điểm đến
# Ưu tiên:
#   A) Link Google Maps -> lấy trực tiếp tọa độ từ chính link (không cần API key)
#   B) Nominatim
#   C) Photon
#   D) ArcGIS World Geocoder
#
# Không có Google Maps API thì không thể sao chép 100% kho POI của Google.
# Vì vậy app cho phép dán link Google Maps để lấy đúng vị trí người dùng đã chọn.

def _extract_coords_from_maps_url(value):
    """Lấy tọa độ từ Google Maps URL, kể cả link rút gọn maps.app.goo.gl."""
    if not value:
        return None, None

    s = value.strip()

    def extract(raw):
        m = re.search(r'@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)', raw)
        if m:
            return float(m.group(1)), float(m.group(2))

        m = re.search(r'!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)', raw)
        if m:
            return float(m.group(1)), float(m.group(2))

        for key in ("query", "destination", "center"):
            m = re.search(
                rf'(?:[?&]{key}=)(-?\d+(?:\.\d+)?)(?:,|%2C)(-?\d+(?:\.\d+)?)',
                raw,
                re.I,
            )
            if m:
                return float(m.group(1)), float(m.group(2))

        return None, None

    lat, lon = extract(s)
    if lat is not None and lon is not None:
        return lat, lon

    # Google Maps thường cho link chia sẻ dạng https://maps.app.goo.gl/...
    # Ta theo redirect để lấy URL đầy đủ rồi bóc tọa độ.
    if "maps.app.goo.gl/" in s or "goo.gl/maps/" in s:
        try:
            res = requests.get(
                s,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=8,
                allow_redirects=True,
            )
            lat, lon = extract(res.url)
            if lat is not None and lon is not None:
                return lat, lon
        except Exception:
            pass

    # Cuối cùng hỗ trợ chuỗi thuần "lat, lon".
    m = re.fullmatch(
        r'\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*', s
    )
    if m:
        return float(m.group(1)), float(m.group(2))

    return None, None



def _geocode_nominatim(q):
    url = (
        "https://nominatim.openstreetmap.org/search"
        f"?q={urllib.parse.quote(q)}&format=json&countrycodes=vn&limit=3"
    )
    res = requests.get(
        url,
        headers={"User-Agent": "DoiXeOmApp_Pro/2.1"},
        timeout=6,
    ).json()
    if not res:
        return None, None
    return float(res[0]["lat"]), float(res[0]["lon"])


def _geocode_photon(q):
    url = f"https://photon.komoot.io/api/?q={urllib.parse.quote(q)}&limit=5"
    res = requests.get(
        url, headers={"User-Agent": "DoiXeOmApp_Pro/2.1"}, timeout=6
    ).json()
    features = res.get("features", [])
    if not features:
        return None, None
    coords = features[0]["geometry"]["coordinates"]
    return float(coords[1]), float(coords[0])


def _geocode_arcgis(q):
    url = (
        "https://geocode-api.arcgis.com/arcgis/rest/services/World/GeocodeServer/"
        f"findAddressCandidates?f=json&singleLine={urllib.parse.quote(q)}&maxLocations=3"
    )
    res = requests.get(
        url, headers={"User-Agent": "DoiXeOmApp_Pro/2.1"}, timeout=7
    ).json()
    candidates = res.get("candidates", [])
    if not candidates:
        return None, None
    loc = candidates[0].get("location", {})
    if "y" in loc and "x" in loc:
        return float(loc["y"]), float(loc["x"])
    return None, None


def lay_toa_do_diem_den(dia_chi):
    if not dia_chi or len(dia_chi.strip()) < 2:
        return None, None

    # Dán link Google Maps => lấy chính xác tọa độ của địa điểm trong link.
    lat, lon = _extract_coords_from_maps_url(dia_chi)
    if lat is not None and lon is not None:
        return lat, lon

    raw_query = dia_chi.strip()
    query_no_postal = re.sub(r"\b\d{5}\b", "", raw_query)
    query_clean = re.sub(r"\s+", " ", query_no_postal).replace(" ,", ",").strip()

    parts = [p.strip() for p in query_clean.split(",")]
    queries_to_try = [query_clean, raw_query]

    if len(parts) >= 2:
        queries_to_try.append(f"{parts[0]}, {parts[1]}, Đồng Nai, Việt Nam")
    if len(parts) >= 3:
        queries_to_try.append(f"{parts[0]}, {parts[1]}, {parts[2]}, Việt Nam")

    seen = set()
    for q in queries_to_try:
        q = q.strip()
        if not q or q.lower() in seen:
            continue
        seen.add(q.lower())

        q_full = (
            q if ("việt nam" in q.lower() or "vietnam" in q.lower())
            else f"{q}, Việt Nam"
        )

        for geocoder in (_geocode_nominatim, _geocode_photon, _geocode_arcgis):
            try:
                lat, lon = geocoder(q_full)
                if lat is not None and lon is not None:
                    return lat, lon
            except Exception:
                pass

    return None, None


# 2. Tính quãng đường bằng OSRM + hệ số an toàn để hạn chế app bị thiếu km
# Lưu ý: OSRM không phải Google Maps nên không thể cam kết trùng 100%.
# Hệ số này được đặt 10% dựa trên trường hợp test 21.82 km so với ~23.9-24 km của Google Maps.
HE_SO_AN_TOAN_CUOC = 1.10


def lam_tron_len_0_1(km):
    return round((km + 0.099999) * 10) / 10


def tinh_so_km_thuc_te(lat1, lon1, lat2, lon2):
    try:
        url = (
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{lon1},{lat1};{lon2},{lat2}"
            f"?overview=false&alternatives=true"
        )
        res = requests.get(url, timeout=7).json()

        routes = res.get("routes", [])
        if not routes:
            return None

        # Lấy tuyến cơ sở và, nếu có, tuyến thay thế dài hơn.
        distances_km = [
            float(route.get("distance", 0)) / 1000.0
            for route in routes
            if route.get("distance") is not None
        ]
        if not distances_km:
            return None

        km_osrm = max(distances_km)

        # Hệ số an toàn chỉ dùng để hạn chế thu thiếu khi dữ liệu OSRM ngắn hơn thực tế.
        km_tinh_cuoc = max(km_osrm, distances_km[0] * HE_SO_AN_TOAN_CUOC)

        return lam_tron_len_0_1(km_tinh_cuoc)
    except Exception:
        return None


# ==========================================
# BƯỚC 1: 🔍 NHẬP ĐIỂM ĐẾN (DÁN TRỰC TIẾP TỪ GOOGLE MAPS)
# ==========================================
col_title, col_refresh = st.columns([8, 1])
with col_title:
    st.subheader("🏁 Nơi bạn muốn đến")
with col_refresh:
    if st.button(
        "🔄 F5",
        help="Tải lại trang và lấy lại dữ liệu vị trí/điểm đến",
        use_container_width=True,
    ):
        st.rerun()

diem_den_chon = st.text_input(
    "🔍 Nhập hoặc dán địa chỉ từ Google Maps vào đây...",
    placeholder="Tên địa điểm, địa chỉ hoặc dán link Google Maps...",
)

st.caption(
    "⭐ Muốn lấy đúng địa điểm Google Maps: nhập tên → mở nút Google Maps bên dưới → chọn đúng địa điểm → "
    "Chia sẻ → Sao chép liên kết → dán link đó vào ô này."
)

lat2, lon2 = None, None

if diem_den_chon and len(diem_den_chon.strip()) >= 2:
    with st.spinner("⏳ Đang tìm địa điểm và đối chiếu tuyến..."):
        lat2, lon2 = lay_toa_do_diem_den(diem_den_chon)
        if lat2 and lon2:
            st.success("✅ Đã tìm thấy điểm đến!")
        else:
            st.warning("⚠️ Chưa tìm thấy địa điểm bằng bộ tìm kiếm miễn phí.")

            google_search_url = (
                "https://www.google.com/maps/search/?api=1&query="
                + urllib.parse.quote(diem_den_chon)
            )
            st.link_button(
                "🌐 TÌM ĐỊA ĐIỂM TRÊN GOOGLE MAPS",
                google_search_url,
                use_container_width=True,
            )
            st.info(
                "💡 Trên Google Maps: chọn đúng địa điểm → Chia sẻ → Sao chép liên kết → "
                "dán liên kết đó vào ô trên. App sẽ lấy tọa độ trực tiếp từ link Google Maps."
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
            st.warning("⚠️ Chưa tính được quãng đường. Vui lòng thử lại sau.")
            so_km = 0.0
            thoi_gian_phut = 0

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

    st.caption(
        f"ℹ️ Km tính cước đã cộng biên độ an toàn {round((HE_SO_AN_TOAN_CUOC - 1) * 100)}% "
        "để hạn chế sai số so với tuyến thực tế."
    )

st.divider()

# ==========================================
# BƯỚC 3: 📞 KẾT NỐI ĐẶT XE (HOTLINE & ZALO)
# ==========================================
HOTLINE = "0978666620"

if diem_den_chon and lat1 and lon1 and so_km > 0:
    maps_url = f"https://www.google.com/maps/dir/?api=1&origin={lat1},{lon1}&destination={urllib.parse.quote(diem_den_chon)}&travelmode=two-wheeler"

    st.markdown(
        f"🧭 **Chỉ đường cho Tài Xế:** [Mở Google Maps]({maps_url})"
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
