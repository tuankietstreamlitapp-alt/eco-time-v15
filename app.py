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



# ============================================================
# V7: TÍNH CƯỚC THEO HÀNH TRÌNH GPS THỰC TẾ
# ============================================================

DONG_GIA = 5000              # VNĐ / km
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
    st.session_state.trip_status = "Đã kết thúc"


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
# GIAO DIỆN
# ============================================================

col_title, col_refresh = st.columns([8, 1])
with col_title:
    st.subheader("🏁 Tính cước theo hành trình thực tế")
with col_refresh:
    if st.button(
        "🔄 F5",
        help="Tải lại trang và lấy lại dữ liệu vị trí",
        use_container_width=True,
    ):
        st.rerun()

st.info(
    "💡 Tài xế chỉ cần bấm **BẮT ĐẦU CUỐC** khi khách lên xe. "
    "App sẽ cộng quãng đường GPS thực tế. Đứng yên thì không cộng tiền. "
    "Khách đổi nhiều điểm đến cũng không cần nhập lại."
)

if not st.session_state.trip_active:
    st.caption("Trạng thái: " + st.session_state.trip_status)
    c1, c2 = st.columns([2, 1])
    with c1:
        if st.button(
            "🟢 BẮT ĐẦU CUỐC",
            use_container_width=True,
            type="primary",
            disabled=False,
        ):
            start_trip()
            st.rerun()
    with c2:
        st.metric("Cước hiện tại", "0 VNĐ")
else:
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button(
            "🔴 KẾT THÚC CUỐC",
            use_container_width=True,
            type="primary",
        ):
            stop_trip()
            st.rerun()
    with c2:
        st.metric("Quãng đường", f"{format_km(st.session_state.trip_total_m)} km")
    with c3:
        st.metric("Cước tạm tính", f"{format_fare(st.session_state.trip_total_m):,.0f} VNĐ")

    st.caption(st.session_state.trip_status)

    # Fragment tự chạy lại khoảng mỗi 2 giây để lấy GPS mới.
    # Nếu môi trường Streamlit quá cũ, app vẫn báo lỗi rõ ràng thay vì tính sai tiền.
    try:
        @st.fragment(run_every=f"{GPS_POLL_SECONDS}s")
        def gps_tracker():
            try:
                loc = get_geolocation()
                process_gps(loc)
            except Exception as exc:
                st.warning(f"⚠️ Chưa đọc được GPS: {exc}")

            st.metric(
                "📍 Tổng quãng đường thực tế",
                f"{format_km(st.session_state.trip_total_m)} km",
            )

            if st.session_state.trip_active:
                st.caption(
                    "📡 GPS đang được cập nhật tự động. "
                    "Nếu trình duyệt hỏi quyền vị trí, hãy chọn Cho phép."
                )

        gps_tracker()
    except Exception:
        # Tương thích với Streamlit không hỗ trợ fragment.
        st.error(
            "⚠️ Phiên bản Streamlit hiện tại chưa hỗ trợ cập nhật GPS tự động. "
            "Cần nâng Streamlit lên phiên bản có st.fragment()."
        )

# Hiển thị hóa đơn khi kết thúc.
if not st.session_state.trip_active and st.session_state.trip_ended_at:
    km = format_km(st.session_state.trip_total_m)
    fare = format_fare(st.session_state.trip_total_m)

    st.divider()
    with st.container(border=True):
        st.subheader("🧾 HÓA ĐƠN CUỐC XEOM4560")
        a, b, c = st.columns(3)
        with a:
            st.metric("📏 Quãng đường", f"{km} km")
        with b:
            st.metric("💰 Đơn giá", f"{DONG_GIA:,.0f} đ/km")
        with c:
            st.metric("💵 TỔNG CƯỚC", f"{fare:,.0f} VNĐ")

        st.success("✅ Cuốc xe đã kết thúc. Có thể thu tiền khách.")

        if st.button("♻️ CUỐC MỚI", use_container_width=True):
            reset_trip()
            st.rerun()

st.divider()
st.caption(
    "🔒 Cơ chế lọc GPS: bỏ điểm có sai số > "
    f"{GPS_ACCURACY_MAX_M} m, bỏ nhiễu < {MIN_MOVE_M} m và bỏ cú nhảy "
    f"GPS tương đương > {MAX_JUMP_SPEED_KMH} km/h."
)
