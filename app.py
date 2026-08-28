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


# =========================================================
# CẤU HÌNH GOOGLE MAPS
# Streamlit Cloud/local: tạo .streamlit/secrets.toml với:
# GOOGLE_MAPS_API_KEY = "YOUR_API_KEY"
# Bật ít nhất: Places API (New) + Routes API
# =========================================================

# 1. Google Maps Places API (New): tìm đúng địa điểm theo dữ liệu Google
def get_google_api_key():
    try:
        return st.secrets.get("GOOGLE_MAPS_API_KEY", "")
    except Exception:
        return ""


def tim_diem_den_google_maps(dia_chi, lat_bias=None, lon_bias=None):
    """Tìm địa điểm bằng Google Places Text Search (New)."""
    if not dia_chi or len(dia_chi.strip()) < 2:
        return None

    api_key = get_google_api_key()
    if not api_key:
        st.error("❌ Chưa cấu hình GOOGLE_MAPS_API_KEY trong Streamlit Secrets.")
        return None

    query = dia_chi.strip()
    if "việt nam" not in query.lower() and "vietnam" not in query.lower():
        query = f"{query}, Việt Nam"

    payload = {
        "textQuery": query,
        "languageCode": "vi",
        "regionCode": "VN",
        "pageSize": 5,
    }

    # Ưu tiên địa điểm gần vị trí đón hiện tại, nhưng vẫn để Google xếp hạng
    # theo mức độ phù hợp của truy vấn.
    if lat_bias is not None and lon_bias is not None:
        payload["locationBias"] = {
            "circle": {
                "center": {"latitude": float(lat_bias), "longitude": float(lon_bias)},
                "radius": 50000.0,
            }
        }

    try:
        res = requests.post(
            "https://places.googleapis.com/v1/places:searchText",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location",
            },
            json=payload,
            timeout=8,
        )
        res.raise_for_status()
        data = res.json()
        places = data.get("places", [])
        if not places:
            return None

        place = places[0]
        loc = place.get("location", {})
        if "latitude" not in loc or "longitude" not in loc:
            return None

        return {
            "place_id": place.get("id"),
            "name": place.get("displayName", {}).get("text", ""),
            "address": place.get("formattedAddress", query),
            "lat": float(loc["latitude"]),
            "lon": float(loc["longitude"]),
        }
    except requests.RequestException as e:
        st.error(f"❌ Google Places API lỗi: {e}")
    except Exception as e:
        st.error(f"❌ Không đọc được kết quả Google Maps: {e}")
    return None


# 2. Google Maps Routes API: tính quãng đường/tgian theo tuyến xe 2 bánh
def tinh_route_google_maps(lat1, lon1, lat2, lon2):
    """Dùng Google Routes API với TWO_WHEELER cho xe máy."""
    api_key = get_google_api_key()
    if not api_key:
        return None

    payload = {
        "origin": {
            "location": {
                "latLng": {"latitude": float(lat1), "longitude": float(lon1)}
            }
        },
        "destination": {
            "location": {
                "latLng": {"latitude": float(lat2), "longitude": float(lon2)}
            }
        },
        "travelMode": "TWO_WHEELER",
        "routingPreference": "TRAFFIC_AWARE",
    }

    try:
        res = requests.post(
            "https://routes.googleapis.com/directions/v2:computeRoutes",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": "routes.distanceMeters,routes.duration,routes.staticDuration",
            },
            json=payload,
            timeout=10,
        )
        res.raise_for_status()
        data = res.json()
        routes = data.get("routes", [])
        if not routes:
            return None

        route = routes[0]
        distance_m = route.get("distanceMeters")
        duration_text = route.get("duration") or route.get("staticDuration")
        if distance_m is None:
            return None

        # Google duration trả về dạng "123s".
        phut = None
        if duration_text:
            m = re.match(r"^(\d+(?:\.\d+)?)s$", duration_text)
            if m:
                phut = round(float(m.group(1)) / 60)

        return round(float(distance_m) / 1000.0, 2), phut
    except requests.RequestException as e:
        st.error(f"❌ Google Routes API lỗi: {e}")
    except Exception as e:
        st.error(f"❌ Không đọc được tuyến Google Maps: {e}")
    return None


# ==========================================
# BƯỚC 1: 🔍 NHẬP ĐIỂM ĐẾN (DÁN TRỰC TIẾP TỪ GOOGLE MAPS)
# ==========================================
st.subheader("🏁 Nơi bạn muốn đến")
diem_den_chon = st.text_input(
    "🔍 Nhập hoặc dán địa chỉ từ Google Maps vào đây...",
    placeholder="Ví dụ: Đồng Hồ Hải Triều, 64 Đ. Đồng Khởi, Tam Hiệp...",
)

lat2, lon2 = None, None
diem_den_google = None

if diem_den_chon and len(diem_den_chon.strip()) >= 2:
    with st.spinner("⏳ Đang tìm địa điểm trên Google Maps..."):
        # Nếu đã có GPS thì dùng GPS làm location bias để Google ưu tiên kết quả gần tài xế.
        bias_lat = locals().get("lat1")
        bias_lon = locals().get("lon1")
        diem_den_google = tim_diem_den_google_maps(diem_den_chon, bias_lat, bias_lon)
        if diem_den_google:
            lat2 = diem_den_google["lat"]
            lon2 = diem_den_google["lon"]
            diem_den_chon = diem_den_google["address"]
            st.success(f"✅ Google Maps: {diem_den_google['name'] or diem_den_google['address']}")
        else:
            st.warning("⚠️ Google Maps không tìm thấy địa điểm phù hợp. Vui lòng nhập tên/địa chỉ rõ hơn.")

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
        route_google = tinh_route_google_maps(lat1, lon1, lat2, lon2)
        if route_google:
            so_km, phut_google = route_google
            thoi_gian_phut = phut_google if phut_google is not None else round((so_km / 30) * 60)
        else:
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
