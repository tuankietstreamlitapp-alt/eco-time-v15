import math
import time
import urllib.parse
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="4567 Xe Ôm", page_icon="🛵", layout="centered"
)

# ============================================================
# GIAO DIỆN 4567 XE ÔM — PHONG CÁCH XANH SM (XANH - SẠCH - UY TÍN)
# ============================================================

st.markdown(
    """
    <style>
    /* Tổng thể nền và font chữ */
    .stApp {
        background-color: #f8fafc;
    }
    
    .block-container {
        max-width: 720px;
        padding-top: 1.2rem;
        padding-bottom: 2.5rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    /* Header chuẩn Xanh SM */
    .app-header {
        background: linear-gradient(135deg, #00A86B 0%, #00804D 100%);
        padding: 20px 24px;
        border-radius: 20px;
        color: white;
        margin-bottom: 16px;
        box-shadow: 0 8px 24px rgba(0, 168, 107, 0.24);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .app-title {
        font-size: 22px;
        font-weight: 900;
        letter-spacing: 0.5px;
        margin: 0;
        color: white;
    }

    .app-subtitle {
        margin: 4px 0 0 0;
        color: #e2e8f0;
        font-size: 13px;
        font-weight: 500;
    }

    .status-badge {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 700;
        background: rgba(255, 255, 255, 0.2);
        color: #ffffff;
        margin-top: 8px;
    }

    /* Khung Thẻ (Card) nội dung */
    .section-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 14px;
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.04);
    }

    .section-title {
        font-size: 15px;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 4px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .section-desc {
        font-size: 13px;
        color: #64748b;
        margin-bottom: 14px;
        line-height: 1.4;
    }

    /* Khung Khẩn Cấp */
    .emergency-box {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 16px;
        padding: 18px;
        margin-top: 16px;
        margin-bottom: 14px;
    }

    .emergency-title {
        color: #166534;
        font-size: 15px;
        font-weight: 800;
        margin-bottom: 4px;
        text-transform: uppercase;
    }

    /* Nút bấm tuỳ chỉnh */
    div.stButton > button {
        border-radius: 12px !important;
        font-weight: 800 !important;
        min-height: 50px !important;
        background-color: #00A86B !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0, 168, 107, 0.2);
        transition: all 0.2s ease;
    }
    
    div.stButton > button:hover {
        background-color: #008f5a !important;
        box-shadow: 0 6px 16px rgba(0, 168, 107, 0.3);
    }

    div.stLinkButton > a {
        border-radius: 12px !important;
        font-weight: 800 !important;
        min-height: 50px !important;
    }

    /* Tối ưu Metric hiển thị số liệu */
    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 12px 14px;
        border-radius: 14px;
    }
    
    div[data-testid="stMetric"] label {
        font-size: 12px !important;
        color: #64748b !important;
        font-weight: 700 !important;
    }

    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 18px !important;
        color: #0f172a !important;
        font-weight: 800 !important;
    }

    .footer-note {
        text-align: center;
        color: #94a3b8;
        font-size: 11px;
        margin-top: 20px;
        line-height: 1.6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# HEADER HIỂN THỊ LOGO & THƯƠNG HIỆU
# ============================================================
col_logo, col_text = st.columns([1, 3.5], vertical_alignment="center")
with col_logo:
    try:
        st.image("logo.png", width=95)
    except Exception:
        st.write("🛵 4567")

with col_text:
    st.markdown(
        """
        <div class="app-header" style="margin-bottom: 0px;">
            <div>
                <div class="app-title">4567 XE ÔM</div>
                <div class="app-subtitle">Xanh • Sạch • An Toàn • Uy Tín</div>
                <div class="status-badge">● Hệ thống Real-time Active</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")

# ============================================================
# CẤU HÌNH THÔNG SỐ CUỐC XE
# ============================================================
DONG_GIA = 5000              # VNĐ / km
HOTLINE = "0978666620"
ZALO_URL = f"https://zalo.me/{HOTLINE}"

GPS_ACCURACY_MAX_M = 60      # Sai số GPS tối đa
MIN_MOVE_M = 4               # Ngưỡng dịch chuyển tối thiểu (mét)

# Xử lý sự kiện dừng cuốc từ JavaScript trả về qua query params
if "action" in st.query_params and st.query_params["action"] == "stop":
    try:
        dist_val = float(st.query_params.get("dist", 0.0))
    except (TypeError, ValueError):
        dist_val = 0.0

    st.session_state.trip_active = False
    st.session_state.trip_ended_at = time.time()
    st.session_state.trip_total_m = dist_val
    st.session_state.trip_status = "Chờ thanh toán"
    st.query_params.clear()
    st.rerun()

# Khởi tạo session_state
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
    st.session_state.trip_started_at = time.time()
    st.session_state.trip_status = "Đang chạy"

def format_km(total_m):
    return round(total_m / 1000.0, 2)

def format_fare(total_m):
    return round((total_m / 1000.0) * DONG_GIA)

# ============================================================
# GIAO DIỆN ĐIỀU KHIỂN & ĐO HÀNH TRÌNH GPS
# ============================================================
col_title, col_refresh = st.columns([7, 1], vertical_alignment="center")
with col_title:
    st.markdown('<div class="section-title" style="margin-bottom:0;">🏁 Điều phối cuốc xe</div>', unsafe_allow_html=True)
with col_refresh:
    if st.button("🔄 F5", help="Tải lại trang nhanh", use_container_width=True):
        st.rerun()

st.write("")

# TRẠNG THÁI 1: CHƯA BẮT ĐẦU
if not st.session_state.trip_active and not st.session_state.trip_ended_at:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">🚦 Sẵn sàng nhận khách</div>
            <div class="section-desc">
                Bấm nút bắt đầu bên dưới để kích hoạt đồng hồ định vị GPS và giữ màn hình luôn sáng suốt hành trình.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🟢 BẮT ĐẦU CUỐC XE", key="btn_start", use_container_width=True):
        start_trip()
        st.rerun()

    st.write("")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Quãng đường", "0,00 km")
    with m2:
        st.metric("Đơn giá", f"{DONG_GIA:,.0f}đ")
    with m3:
        st.metric("Cước tạm tính", "0 VNĐ")

# TRẠNG THÁI 2: ĐANG CHẠY (REAL-TIME GPS + WAKE LOCK)
elif st.session_state.trip_active:
    st.markdown(
        """
        <div class="section-card" style="border-color: #00A86B; background: #fdfdfd;">
            <div class="section-title" style="color: #00A86B;">🟢 Hành trình đang diễn ra</div>
            <div class="section-desc" style="margin-bottom: 0;">
                Hệ thống đang ghi nhận quãng đường thực tế và bảo vệ màn hình không bị tắt.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    html_live_tracker = f"""
    <div style="font-family: sans-serif; padding: 16px; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.02);">
        <div style="background: linear-gradient(135deg, #f0fdf4 0%, #e6f4ed 100%); border: 1px solid #bbf7d0; border-radius: 14px; padding: 16px; margin-bottom: 14px;">
            <div style="color: #166534; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px;">Cước phí tạm tính</div>
            <div id="price" style="color: #0f172a; font-size: 34px; font-weight: 900; letter-spacing: -1px; margin: 4px 0;">0 VNĐ</div>
            <div style="color: #475569; font-size: 12px;"><span id="km">0.00</span> km • {DONG_GIA:,.0f} đ/km</div>
        </div>

        <div style="display: flex; gap: 10px; margin-bottom: 14px;">
            <div style="flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; padding: 10px; border-radius: 12px; text-align: left;">
                <div style="font-size: 11px; color: #64748b; font-weight: 700;">📏 Quãng đường</div>
                <div id="dist_display" style="font-size: 16px; font-weight: 800; color: #0f172a; margin-top: 2px;">0.00 km</div>
            </div>
            <div style="flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; padding: 10px; border-radius: 12px; text-align: left;">
                <div style="font-size: 11px; color: #64748b; font-weight: 700;">🛡️ Trạng thái Khóa</div>
                <div id="wakelock_status" style="font-size: 11px; font-weight: 700; color: #00A86B; margin-top: 2px;">Đang giữ sáng màn hình...</div>
            </div>
        </div>

        <button onclick="stopTrip()" style="width: 100%; background: #0f172a; color: white; border: none; border-radius: 12px; padding: 14px; font-size: 15px; font-weight: 800; cursor: pointer; box-shadow: 0 4px 12px rgba(15,23,42,0.15);">
            💳 KẾT THÚC & THANH TOÁN
        </button>
        <div id="debug_acc" style="font-size: 11px; color: #94a3b8; margin-top: 8px;">GPS: Đang định vị...</div>
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
                document.getElementById("wakelock_status").innerText = "Đã khóa sáng ✅";
            }} else {{
                document.getElementById("wakelock_status").innerText = "Trình duyệt không hỗ trợ WakeLock";
            }}
        }} catch (err) {{
            document.getElementById("wakelock_status").innerText = "Chạm màn hình để kích hoạt";
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

                if (acc > maxAccuracy) return;

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

    // SỬA LỖI ĐIỀU HƯỚNG BẰNG THẺ LINK TARGET _TOP
    function stopTrip() {{
        localStorage.removeItem("xeom_total_meters");
        if (wakeLock !== null) {{
            wakeLock.release().catch(() => {{}});
        }}
        
        let parentUrl = document.referrer ? document.referrer.split('?')[0] : window.location.href.split('?')[0];
        let targetUrl = parentUrl + "?action=stop&dist=" + totalMeters;
        
        let a = document.createElement("a");
        a.href = targetUrl;
        a.target = "_top";
        document.body.appendChild(a);
        a.click();
    }}
    </script>
    """
    components.html(html_live_tracker, height=270)

# TRẠNG THÁI 3: HOÀN THÀNH CUỐC XE & THANH TOÁN
if not st.session_state.trip_active and st.session_state.trip_ended_at:
    km = format_km(st.session_state.trip_total_m)
    fare = format_fare(st.session_state.trip_total_m)

    # NHÚNG BẮN PHÁO HOA CHUẨN
    components.html(
        """
        <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.browser.min.js"></script>
        <script>
            setTimeout(() => {
                confetti({
                    particleCount: 120,
                    spread: 80,
                    origin: { y: 0.5 }
                });
            }, 300);
        </script>
        """,
        height=1,
    )

    st.markdown(
        """
        <div class="section-card" style="border-color: #00A86B;">
            <div class="section-title" style="color: #00A86B;">🎉 HOÀN THÀNH CUỐC XE</div>
            <div class="section-desc">Hành trình đã kết thúc an toàn. Tóm tắt thông tin thanh toán:</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    a, b, c = st.columns(3)
    with a:
        st.metric("📏 Quãng đường", f"{km:.2f} km")
    with b:
        st.metric("💰 Đơn giá", f"{DONG_GIA:,.0f}đ")
    with c:
        st.metric("💵 Tổng cước", f"{fare:,.0f} VNĐ")

    st.success("✅ Thanh toán thành công! Cảm ơn khách hàng đã đồng hành cùng đội.")
    
    st.write("")
    if st.button("♻️ BẮT ĐẦU CUỐC MỚI", use_container_width=True):
        reset_trip()
        st.rerun()

# ============================================================
# KHU VỰC HỖ TRỢ & LIÊN HỆ KHẨN CẤP
# ============================================================
st.markdown(
    """
    <div class="emergency-box">
        <div class="emergency-title">🆘 HỖ TRỢ & ĐIỀU PHỐI KHẨN CẤP</div>
        <div class="section-desc" style="margin-bottom: 10px;">Khi cần hỗ trợ kỹ thuật hoặc liên hệ trung tâm đội xe:</div>
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
        "💬 ZALO ĐỘI XE",
        ZALO_URL,
        use_container_width=True,
    )

st.markdown(
    f"""
    <div class="footer-note">
        🛡️ Chống F5 LocalStorage • Khóa màn hình WakeLock Active<br>
        <b>4567 Xe Ôm</b> • Xanh • Sạch • An Toàn • Uy Tín
    </div>
    """,
    unsafe_allow_html=True,
)
