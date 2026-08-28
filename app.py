import re
import math
import urllib.parse
import requests
import streamlit as st
from streamlit_js_eval import get_geolocation

st.set_page_config(
    page_title="Đội Xe Ôm Tin Cẩn", page_icon="🛵", layout="centered"
)

live_gps_tracker()

# ============================================================
# GIAO DIỆN XEOM4560 — phong cách hiện đại, sạch, dễ bấm
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        max-width: 760px;
        padding-top: 1.0rem;
        padding-bottom: 2rem;
    }

    .app-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 22px 24px;
        border-radius: 20px;
        color: white;
        margin-bottom: 18px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.16);
    }

    .app-brand {
        font-size: 30px;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin: 0;
    }

    .app-subtitle {
        margin: 6px 0 0 0;
        color: #cbd5e1;
        font-size: 14px;
    }

    .status-pill {
        display: inline-block;
        margin-top: 14px;
        padding: 6px 11px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
        background: rgba(255,255,255,.10);
        color: #e2e8f0;
    }

    .section-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 18px 18px 10px 18px;
        margin: 12px 0;
        box-shadow: 0 6px 20px rgba(15,23,42,.06);
    }

    .section-title {
        font-size: 16px;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 2px;
    }

    .section-desc {
        font-size: 13px;
        color: #64748b;
        margin-bottom: 12px;
    }

    .fare-hero {
        background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
        border: 1px solid #dbeafe;
        border-radius: 18px;
        padding: 18px;
        text-align: center;
        margin: 12px 0;
    }

    .fare-label {
        color: #64748b;
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .7px;
    }

    .fare-value {
        color: #0f172a;
        font-size: 38px;
        font-weight: 900;
        letter-spacing: -1px;
        margin: 5px 0;
    }

    .fare-note {
        color: #64748b;
        font-size: 12px;
    }

    .emergency-box {
        background: #fff7ed;
        border: 1px solid #fed7aa;
        border-radius: 18px;
        padding: 17px 18px 8px 18px;
        margin-top: 18px;
    }

    .emergency-title {
        color: #9a3412;
        font-size: 16px;
        font-weight: 800;
        margin-bottom: 2px;
    }

    div.stButton > button,
    div.stLinkButton > a {
        border-radius: 12px !important;
        font-weight: 800 !important;
        min-height: 46px !important;
    }

    div[data-testid="stMetric"] {
        background: rgba(255,255,255,.72);
        border: 1px solid #e2e8f0;
        padding: 10px 12px;
        border-radius: 14px;
    }

    .footer-note {
        text-align: center;
        color: #94a3b8;
        font-size: 11px;
        margin-top: 14px;
        line-height: 1.5;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="app-header">
        <div class="app-brand">🛵 Xeom4560</div>
        <div class="app-subtitle">Tính cước theo hành trình thực tế • Minh bạch • Nhanh • Dễ dùng</div>
        <div class="status-pill">● Hệ thống sẵn sàng</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# V7: TÍNH CƯỚC THEO HÀNH TRÌNH GPS THỰC TẾ
# ============================================================

DONG_GIA = 5000              # VNĐ / km
HOTLINE = "0978666620"
ZALO_URL = f"https://zalo.me/{HOTLINE}"

GPS_ACCURACY_MAX_M = 50      # Bỏ điểm GPS có sai số lớn hơn mức này
MIN_MOVE_M = 10              # Bỏ nhiễu GPS nhỏ hơn 10 m
MAX_JUMP_SPEED_KMH = 120     # Loại trừ cú nhảy GPS bất thường
GPS_POLL_SECONDS = 2         # Cập nhật khoảng mỗi 2 giây

# Khởi tạo trạng thái cuốc xe.
defaults = {
    "trip_active": False,
    "trip_started_at": None,
    "trip_ended_at": None,
    "trip_total_m": 0.0,
    "trip_points": [],
    "trip_last_lat": None,
    "trip_last_lon": None,
    "trip_last_ts": None,
    "trip_last_accuracy": None,
    "trip_status": "Chưa bắt đầu",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def haversine_m(lat1, lon1, lat2, lon2):
    """Khoảng cách đường chim bay giữa 2 điểm GPS, đơn vị mét."""
    r = 6_371_000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    )
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))


def reset_trip():
    st.session_state.trip_active = False
    st.session_state.trip_started_at = None
    st.session_state.trip_ended_at = None
    st.session_state.trip_total_m = 0.0
    st.session_state.trip_points = []
    st.session_state.trip_last_lat = None
    st.session_state.trip_last_lon = None
    st.session_state.trip_last_ts = None
    st.session_state.trip_last_accuracy = None
    st.session_state.trip_status = "Chưa bắt đầu"


def start_trip():
    reset_trip()
    st.session_state.trip_active = True
    st.session_state.trip_started_at = __import__("time").time()
    st.session_state.trip_status = "Đang chạy"


def stop_trip():
    st.session_state.trip_active = False
    st.session_state.trip_ended_at = __import__("time").time()
    st.session_state.trip_status = "Chờ thanh toán"


def process_gps(loc):
    """Lọc nhiễu GPS rồi cộng dồn quãng đường thực tế."""
    if not st.session_state.trip_active:
        return

    if not loc or "coords" not in loc:
        st.session_state.trip_status = "Đang chờ GPS..."
        return

    coords = loc.get("coords", {})
    lat = coords.get("latitude")
    lon = coords.get("longitude")
    accuracy = coords.get("accuracy")
    timestamp = loc.get("timestamp")

    if lat is None or lon is None:
        return

    try:
        lat = float(lat)
        lon = float(lon)
        accuracy = float(accuracy) if accuracy is not None else 999.0
        ts = float(timestamp) / 1000.0 if timestamp else __import__("time").time()
    except (TypeError, ValueError):
        return

    # Không cộng khi GPS quá sai.
    if accuracy > GPS_ACCURACY_MAX_M:
        st.session_state.trip_last_accuracy = accuracy
        st.session_state.trip_status = f"GPS đang sai số ~{accuracy:.0f} m — tạm không tính"
        return

    last_lat = st.session_state.trip_last_lat
    last_lon = st.session_state.trip_last_lon
    last_ts = st.session_state.trip_last_ts

    # Điểm GPS đầu tiên: lấy làm mốc, chưa cộng km.
    if last_lat is None or last_lon is None or last_ts is None:
        st.session_state.trip_last_lat = lat
        st.session_state.trip_last_lon = lon
        st.session_state.trip_last_ts = ts
        st.session_state.trip_last_accuracy = accuracy
        st.session_state.trip_points.append(
            {"lat": lat, "lon": lon, "ts": ts, "accuracy": accuracy}
        )
        st.session_state.trip_status = "Đã khóa vị trí bắt đầu"
        return

    distance_m = haversine_m(last_lat, last_lon, lat, lon)
    dt = max(0.5, ts - last_ts)
    speed_kmh = (distance_m / dt) * 3.6

    # Bỏ rung GPS nhỏ.
    if distance_m < MIN_MOVE_M:
        st.session_state.trip_status = f"Đang theo dõi • GPS ±{accuracy:.0f} m"
        return

    # Bỏ cú nhảy GPS bất thường.
    if speed_kmh > MAX_JUMP_SPEED_KMH:
        st.session_state.trip_status = "Phát hiện GPS nhảy bất thường — bỏ đoạn này"
        return

    st.session_state.trip_total_m += distance_m
    st.session_state.trip_last_lat = lat
    st.session_state.trip_last_lon = lon
    st.session_state.trip_last_ts = ts
    st.session_state.trip_last_accuracy = accuracy
    st.session_state.trip_points.append(
        {
            "lat": lat,
            "lon": lon,
            "ts": ts,
            "accuracy": accuracy,
            "segment_m": distance_m,
            "speed_kmh": speed_kmh,
        }
    )
    st.session_state.trip_status = f"Đang chạy • GPS ±{accuracy:.0f} m"


def format_km(total_m):
    return round(total_m / 1000.0, 2)


def format_fare(total_m):
    return round((total_m / 1000.0) * DONG_GIA)



# ============================================================
# GPS LIVE TRACKER
# ============================================================
# Quan trọng: fragment được khai báo SAU GPS_POLL_SECONDS và các hàm GPS.
# Đồng thời get_geolocation() luôn được mount ổn định, không nằm trong if/else.
@st.fragment(run_every=f"{GPS_POLL_SECONDS}s")
def live_gps_tracker():
    loc = None

    try:
        loc = get_geolocation()
    except Exception as exc:
        if st.session_state.trip_active:
            st.warning(f"⚠️ Không đọc được GPS: {exc}")

    if not st.session_state.trip_active:
        return

    if loc and isinstance(loc, dict) and "error" in loc:
        err = loc.get("error", {})
        code = err.get("code", "")
        message = err.get("message", "Không xác định")
        st.session_state.trip_status = f"GPS lỗi {code}: {message}"
    else:
        process_gps(loc)

    km_now = format_km(st.session_state.trip_total_m)
    fare_now = format_fare(st.session_state.trip_total_m)

    st.markdown(
        f"""
        <div class="fare-hero">
            <div class="fare-label">Tổng cước tạm tính</div>
            <div class="fare-value">{fare_now:,.0f} VNĐ</div>
            <div class="fare-note">{km_now:.2f} km • {DONG_GIA:,.0f} đ/km</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    a, b = st.columns(2)
    with a:
        st.metric("📏 Quãng đường", f"{km_now:.2f} km")
    with b:
        st.metric("📡 GPS", st.session_state.trip_status)

    accuracy = st.session_state.trip_last_accuracy
    if accuracy is not None:
        st.caption(
            f"GPS đang cập nhật • Sai số lần cuối ±{accuracy:.0f} m • "
            f"Tự động cập nhật mỗi {GPS_POLL_SECONDS} giây."
        )
    else:
        st.caption(
            "📍 Đang chờ vị trí GPS đầu tiên... "
            "Hãy cho phép trình duyệt truy cập vị trí."
        )


# ============================================================
# GIAO DIỆN
# ============================================================

col_title, col_refresh = st.columns([8, 1])
with col_title:
    st.markdown('<div class="section-title">🏁 Điều khiển cuốc xe</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-desc">Một nút duy nhất: BẮT ĐẦU CUỐC → THANH TOÁN.</div>',
        unsafe_allow_html=True,
    )
with col_refresh:
    if st.button(
        "🔄 F5",
        help="Tải lại trang và lấy lại dữ liệu vị trí",
        use_container_width=True,
    ):
        st.rerun()

if not st.session_state.trip_active:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">🚦 Sẵn sàng nhận cuốc</div>
            <div class="section-desc">
                Chưa phát sinh cước. Khi xe đứng yên, tiền không tăng.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "🟢  BẮT ĐẦU CUỐC",
        key="trip_action_button",
        use_container_width=True,
        type="primary",
    ):
        start_trip()
        st.rerun()

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Quãng đường", "0,00 km")
    with m2:
        st.metric("Đơn giá", f"{DONG_GIA:,.0f} đ/km")
    with m3:
        st.metric("Cước hiện tại", "0 VNĐ")

else:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">🟢 Cuốc xe đang chạy</div>
            <div class="section-desc">
                GPS đang theo dõi hành trình thực tế. Không cần nhập điểm đến.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "💳  THANH TOÁN",
        key="trip_action_button",
        use_container_width=True,
        type="primary",
    ):
        stop_trip()
        st.rerun()

    st.markdown(
        '<div class="footer-note">Khách có thể phát sinh nhiều điểm đến trong cùng một cuốc • App chỉ tính quãng đường GPS hợp lệ.</div>',
        unsafe_allow_html=True,
    )

# Hiển thị hóa đơn khi kết thúc.
if not st.session_state.trip_active and st.session_state.trip_ended_at:
    km = format_km(st.session_state.trip_total_m)
    fare = format_fare(st.session_state.trip_total_m)

    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">🧾 THANH TOÁN XEOM4560</div>
            <div class="section-desc">Cuốc xe đã sẵn sàng thanh toán.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    a, b, c = st.columns(3)
    with a:
        st.metric("📏 Quãng đường", f"{km:.2f} km")
    with b:
        st.metric("💰 Đơn giá", f"{DONG_GIA:,.0f} đ/km")
    with c:
        st.metric("💵 Tổng cước", f"{fare:,.0f} VNĐ")

    st.success("✅ Đã chốt tiền. Có thể thu tiền khách.")

    if st.button("♻️  BẮT ĐẦU CUỐC MỚI", use_container_width=True):
        reset_trip()
        st.rerun()

st.markdown(
    """
    <div class="emergency-box">
        <div class="emergency-title">🆘 LIÊN HỆ KHẨN CẤP</div>
        <div class="section-desc">Khi có sự cố hoặc cần điều phối, liên hệ Đội Xeom4560.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

c_hotline, c_zalo = st.columns(2)
with c_hotline:
    st.link_button(
        f"📞 GỌI {HOTLINE}",
        f"tel:{HOTLINE}",
        use_container_width=True,
        type="primary",
    )
with c_zalo:
    st.link_button(
        "💬 LIÊN HỆ ZALO",
        ZALO_URL,
        use_container_width=True,
    )

st.markdown(
    f"""
    <div class="footer-note">
        🔒 Bộ lọc GPS: sai số &gt; {GPS_ACCURACY_MAX_M} m không cộng •
        nhiễu &lt; {MIN_MOVE_M} m bỏ qua • cú nhảy &gt; {MAX_JUMP_SPEED_KMH} km/h bỏ qua.
        <br>Xeom4560 • Cước minh bạch theo hành trình thực tế.
    </div>
    """,
    unsafe_allow_html=True,
)
