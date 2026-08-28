import re
import math
import urllib.parse
import requests
import streamlit as st
from streamlit_js_eval import get_geolocation

st.set_page_config(
    page_title="Đội Xe Ôm Tin Cẩn", page_icon="🛵", layout="centered"
)

# ============================================================
# GPS LIVE TRACKER
# ============================================================

# IMPORTANT:
# get_geolocation() must be called from a stable, unconditional fragment.
# streamlit-js-eval documents limitations when called inside Streamlit branches.
@st.fragment(run_every=f"{GPS_POLL_SECONDS}s")
def live_gps_tracker():
    loc = None
    try:
        # Keep this component call at the top of the fragment, not inside
        # if/else branches.
        loc = get_geolocation()
    except Exception as exc:
        if st.session_state.trip_active:
            st.warning(f"⚠️ Không đọc được GPS: {exc}")

    if st.session_state.trip_active:
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
                "📍 Đang chờ vị trí GPS đầu tiên... Hãy cho phép trình duyệt truy cập vị trí."
            )


# ============================================================
# GIAO DIỆN
# ============================================================

col_title, col_refresh = st.columns([8, 1])
with col_title:
    st.markdown(
        '<div class="section-title">🏁 Điều khiển cuốc xe</div>',
        unsafe_allow_html=True,
    )
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

# Live tracker is always mounted, so the browser GPS component is not
# conditionally created. It simply processes GPS only while a trip is active.
live_gps_tracker()

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

    # The live GPS / fare display is rendered above in live_gps_tracker().
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
