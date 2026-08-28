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

# Một vị trí duy nhất cho nút điều khiển.
if not st.session_state.trip_active:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">🚦 Sẵn sàng nhận cuốc</div>
            <div class="section-desc">
                Bấm nút bên dưới khi khách đã lên xe. App bắt đầu ghi nhận GPS từ thời điểm đó.
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

    try:
        @st.fragment(run_every=f"{GPS_POLL_SECONDS}s")
        def gps_tracker():
            try:
                loc = get_geolocation()
                process_gps(loc)
            except Exception as exc:
                st.warning(f"⚠️ Chưa đọc được GPS: {exc}")

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

            st.caption(
                "GPS đang cập nhật tự động. Hãy để trình duyệt được phép truy cập vị trí."
            )

        gps_tracker()
    except Exception:
        st.error(
            "⚠️ Phiên bản Streamlit hiện tại chưa hỗ trợ cập nhật GPS tự động. "
            "Cần nâng Streamlit lên phiên bản có st.fragment()."
        )

    # Cùng đúng vị trí với nút BẮT ĐẦU CUỐC, chỉ đổi tên thành THANH TOÁN.
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

    if st.button("♻️  CUỐC MỚI", use_container_width=True):
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
