import math
import urllib.parse
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="4567 Xe Ôm", page_icon="🛵", layout="centered"
)

# ============================================================
# GIAO DIỆN 4567 XE ÔM — Bản chuẩn có Logo, Chống F5 & Wake Lock
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

# Hiển thị Logo và Tiêu đề Header
col_logo, col_text = st.columns([1, 3])
with col_logo:
    try:
        st.image("logo.png", width=110)
    except Exception:
        st.write("🛵 4567")

with col_text:
    st.markdown(
        """
        <div class="app-header" style="margin-bottom: 0px; padding: 16px 20px;">
            <div style="font-size: 24px; font-weight: 800; color: white; margin: 0;">4567 XE ÔM</div>
            <div class="app-subtitle">Chống F5 • Giữ màn hình sáng • Xã hội xanh</div>
            <div class="status-pill">● Hoạt động Real-time Active</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")

# ============================================================
# CẤU HÌNH & TRẠNG THÁI CUỐC XE
# ============================================================

DONG_GIA = 5000              # VNĐ / km
HOTLINE = "0978666620"
ZALO_URL = f"https://zalo.me/{HOTLINE}"

GPS_ACCURACY_MAX_M = 60      # Sai số GPS tối đa cho phép
MIN_MOVE_M = 4               # Ngưỡng dịch chuyển tối thiểu (mét)

# Kiểm tra nếu có request dừng cuốc từ JavaScript trả về qua query params
if "action" in st.query_params and st.query_params["action"] == "stop":
    try:
        dist_val = float(st.query_params.get("dist", 0.0))
    except (TypeError, ValueError):
        dist_val = 0.0

    st.session_state.trip_active = False
    st.session_state.trip_ended_at = __import__("time").time()
    st.session_state.trip_total_m = dist_val
    st.session_state.trip_status = "Chờ thanh toán"
    st.query_params.clear()
    st.rerun()

# Khởi tạo trạng thái session_state
defaults = {
    "trip_active": False,
    "trip_started_at": None,
    "trip_ended_at": None,
    "trip_total_m": 0.0,
    "trip_status": "Chưa bắt đầu",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

def reset_trip():
    st.session_state.trip_active = False
    st.session_state.trip_started_at = None
    st.session_state.trip_ended_at = None
    st.session_state.trip_total_m = 0.0
    st.session_state.trip_status = "Chưa bắt đầu"

def start_trip():
    reset_trip()
    st.session_state.trip_active = True
    st.session_state.trip_started_at = __import__("time").time()
    st.session_state.trip_status = "Đang chạy"

def format_km(total_m):
    return round(total_m / 1000.0, 2)

def format_fare(total_m):
    return round((total_m / 1000.0) * DONG_GIA)

# ============================================================
# GIAO DIỆN ĐIỀU KHIỂN & TRÌNH THEO DÕI GPS
# ============================================================

col_title, col_refresh = st.columns([8, 1])
with col_title:
    st.markdown('<div class="section-title">🏁 Điều khiển cuốc xe</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-desc">Tự động chống treo máy và lưu trữ dữ liệu an toàn khi F5.</div>',
        unsafe_allow_html=True,
    )
with col_refresh:
    if st.button(
        "🔄 F5",
        help="Tải lại trang an toàn",
        use_container_width=True,
    ):
        st.rerun()

if not st.session_state.trip_active and not st.session_state.trip_ended_at:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">🚦 Sẵn sàng nhận cuốc</div>
            <div class="section-desc">
                Bấm nút bắt đầu bên dưới. Màn hình điện thoại sẽ được giữ sáng và tự động bảo vệ dữ liệu hành trình.
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

elif st.session_state.trip_active:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">🟢 Cuốc xe đang chạy (GPS Real-time + Wake Lock)</div>
            <div class="section-desc">
                Hệ thống đang ghi nhận hành trình và khóa màn hình không cho ngủ đông.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    html_live_tracker = f"""
    <div style="font-family: sans-serif; padding: 20px; background: #ffffff; border-radius: 18px; border: 1px solid #e2e8f0; box-shadow: 0 6px 20px rgba(15,23,42,.06); text-align: center;">
        <div style="background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%); border: 1px solid #dbeafe; border-radius: 18px; padding: 18px; margin-bottom: 16px;">
            <div style="color: #64748b; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .7px;">Tổng cước tạm tính</div>
            <div id="price" style="color: #0f172a; font-size: 38px; font-weight: 900; letter-spacing: -1px; margin: 5px 0;">0 VNĐ</div>
            <div style="color: #64748b; font-size: 12px;"><span id="km">0.00</span> km • {DONG_GIA:,.0f} đ/km</div>
        </div>

        <div style="display: flex; gap: 10px; margin-bottom: 16px;">
            <div style="flex: 1; background: rgba(255,255,255,.72); border: 1px solid #e2e8f0; padding: 12px; border-radius: 14px; text-align: left;">
                <div style="font-size: 12px; color: #64748b; font-weight: 600;">📏 Quãng đường</div>
                <div id="dist_display" style="font-size: 18px; font-weight: 800; color: #0f172a; margin-top: 4px;">0.00 km</div>
            </div>
            <div style="flex: 1; background: rgba(255,255,255,.72); border: 1px solid #e2e8f0; padding: 12px; border-radius: 14px; text-align: left;">
                <div style="font-size: 12px; color: #64748b; font-weight: 600;">🛡️ Trạng thái Chống Treo</div>
                <div id="wakelock_status" style="font-size: 12px; font-weight: 700; color: #2563eb; margin-top: 4px;">Đang giữ sáng màn hình...</div>
            </div>
        </div>

        <button onclick="stopTrip()" style="width: 100%; background: #0f172a; color: white; border: none; border-radius: 12px; padding: 14px; font-size: 16px; font-weight: 800; cursor: pointer; box-shadow: 0 4px 12px rgba(15,23,42,0.2);">
            💳 THANH TOÁN
        </button>
        <div id="debug_acc" style="font-size: 11px; color: #94a3b8; margin-top: 10px;">GPS: Đang khởi tạo...</div>
    </div>

    <script>
    function calcCrow(lat1, lon1, lat2, lon2) {{
        var R = 6371000;
        var dLat = (lat2 - lat1) * Math.PI / 180;
        var dLon = (lon2 - lon1) * Math.PI / 180;
        var a = Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon/2) * Math.sin(dLon/2);
        var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }}

    let lastLat = null;
    let lastLon = null;
    let totalMeters = parseFloat(localStorage.getItem("xeom_total_meters") || "0.0");
    
    const dongGia = {DONG_GIA};
    const maxAccuracy = {GPS_ACCURACY_MAX_M};
    const minMove = {MIN_MOVE_M};

    if (totalMeters > 0) {{
        let km = totalMeters / 1000.0;
        let fare = km * dongGia;
        document.getElementById("km").innerText = km.toFixed(2);
        document.getElementById("dist_display").innerText = km.toFixed(2) + " km";
        document.getElementById("price").innerText = Math.round(fare).toLocaleString('vi-VN') + " VNĐ";
    }}

    let wakeLock = null;
    async function requestWakeLock() {{
        try {{
            if ('wakeLock' in navigator) {{
                wakeLock = await navigator.wakeLock.request('screen');
                document.getElementById("wakelock_status").innerText = "Đã khóa sáng màn hình ✅";
                document.getElementById("wakelock_status").style.color = "#16a34a";
            }} else {{
                document.getElementById("wakelock_status").innerText = "Trình duyệt không hỗ trợ WakeLock";
            }}
        }} catch (err) {{
            document.getElementById("wakelock_status").innerText = "Chạm màn hình để kích hoạt khóa";
        }}
    }}
    requestWakeLock();

    document.addEventListener("visibilitychange", async () => {{
        if (wakeLock !== null && document.visibilityState === "visible") {{
            await requestWakeLock();
        }}
    }});

    if ("geolocation" in navigator) {{
        navigator.geolocation.watchPosition(
            function(position) {{
                let lat = position.coords.latitude;
                let lon = position.coords.longitude;
                let acc = position.coords.accuracy;
                
                document.getElementById("debug_acc").innerText = "Sai số GPS: ±" + acc.toFixed(1) + " m";

                if (acc > maxAccuracy) {{
                    return;
                }}

                if (lastLat === null || lastLon === null) {{
                    lastLat = lat;
                    lastLon = lon;
                    return;
                }}

                let d = calcCrow(lastLat, lastLon, lat, lon);
                if (d >= minMove && d < 120) {{
                    totalMeters += d;
                    lastLat = lat;
                    lastLon = lon;
                    
                    localStorage.setItem("xeom_total_meters", totalMeters);
                    
                    let km = totalMeters / 1000.0;
                    let fare = km * dongGia;

                    document.getElementById("km").innerText = km.toFixed(2);
                    document.getElementById("dist_display").innerText = km.toFixed(2) + " km";
                    document.getElementById("price").innerText = Math.round(fare).toLocaleString('vi-VN') + " VNĐ";
                }}
            }},
            function(error) {{
                document.getElementById("debug_acc").innerText = "Lỗi GPS: " + error.message;
            }},
            {{
                enableHighAccuracy: true,
                maximumAge: 0,
                timeout: 15000
            }}
        );
    }} else {{
        document.getElementById("debug_acc").innerText = "Trình duyệt không hỗ trợ GPS";
    }}

    function stopTrip() {{
        localStorage.removeItem("xeom_total_meters");
        if (wakeLock !== null) {{
            wakeLock.release().catch(() => {{}});
        }}
        window.parent.location.href = window.parent.location.pathname + "?action=stop&dist=" + totalMeters;
    }}
    </script>
    """
    components.html(html_live_tracker, height=280)

# Hiển thị hóa đơn kèm hiệu ứng pháo giấy (Confetti) khi kết thúc cuốc
if not st.session_state.trip_active and st.session_state.trip_ended_at:
    km = format_km(st.session_state.trip_total_m)
    fare = format_fare(st.session_state.trip_total_m)

    st.markdown(
        """
        <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.browser.min.js"></script>
        <script>
            confetti({
                particleCount: 120,
                spread: 70,
                origin: { y: 0.6 }
            });
        </script>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">🎉 HOÀN THÀNH CUỐC XE</div>
            <div class="section-desc">Hành trình đã kết thúc an toàn. Thông tin thanh toán chi tiết:</div>
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

    st.success("✅ Đã thanh toán thành công! Cảm ơn khách hàng đã ủng hộ Đội 4567 Xe Ôm.")

    if st.button("♻️  BẮT ĐẦU CUỐC MỚI", use_container_width=True):
        reset_trip()
        st.rerun()

st.markdown(
    """
    <div class="emergency-box">
        <div class="emergency-title">🆘 LIÊN HỆ KHẨN CẤP</div>
        <div class="section-desc">Khi cần hỗ trợ kỹ thuật hoặc điều phối xe, liên hệ ngay.</div>
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
        🛡️ Chống F5 LocalStorage • Khóa màn hình WakeLock Active<br>
        4567 Xe Ôm • Lan tỏa giá trị lao động chân chính và xã hội xanh.
    </div>
    """,
    unsafe_allow_html=True,
)
