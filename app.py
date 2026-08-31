import time
import datetime
import json
import html

import gspread
import pytz
import streamlit as st
import streamlit.components.v1 as components
from google.oauth2.service_account import Credentials


st.set_page_config(
    page_title="4567 Xe Ôm — Tài Xế",
    page_icon="🛵",
    layout="centered",
)

# ============================================================
# 4567 XE ÔM — NGUYÊN TẮC GỐC
# 1. Thao tác đơn giản.
# 2. Giao diện trực quan, ưu tiên người lớn tuổi.
# 3. KM / GPS / THỜI GIAN / THÀNH TIỀN phải nhất quán và minh bạch.
# 4. Luồng thanh toán chỉ trong một trang, không lồng Streamlit vào Streamlit.
# ============================================================

VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")
GPS_ACCURACY_MAX_M = 50.0
MIN_MOVE_M = 3.0
MAX_SEGMENT_M = 250.0
MAX_SPEED_MPS = 45.0  # ~162 km/h, dùng để loại điểm nhảy GPS bất thường.


def get_vn_time(timestamp=None):
    if timestamp is None:
        return datetime.datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    return datetime.datetime.fromtimestamp(float(timestamp), VN_TZ).strftime("%Y-%m-%d %H:%M:%S")


def safe_html(value):
    return html.escape(str(value or ""), quote=True)


# ============================================================
# GOOGLE SHEETS
# ============================================================
SHEET_KEY = st.secrets["connections"]["gsheets"].get(
    "spreadsheet", "1A3-1am25vZLN57SD7pkfxxQtymCaPnCj9HgBpw5RcTY"
)


@st.cache_resource
def init_google_sheet_client():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = dict(st.secrets["connections"]["gsheets"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)


def get_worksheet_data(tab_name):
    try:
        client = init_google_sheet_client()
        sheet = client.open_by_key(SHEET_KEY)
        ws = sheet.worksheet(tab_name)
        return ws, ws.get_all_records()
    except Exception:
        return None, []


def append_row_to_sheet(tab_name, row_values):
    try:
        client = init_google_sheet_client()
        sheet = client.open_by_key(SHEET_KEY)
        ws = sheet.worksheet(tab_name)
        ws.append_row(row_values, value_input_option="USER_ENTERED")
        return True
    except Exception:
        return False


def delete_row_status(tab_name, col_name, target_val):
    """Return 'deleted', 'not_found', or 'error'."""
    try:
        ws, records = get_worksheet_data(tab_name)
        if ws is None:
            return "error"
        target = str(target_val).strip()
        for row_index, row in enumerate(records, start=2):
            if str(row.get(col_name, "")).strip() == target:
                ws.delete_rows(row_index)
                return "deleted"
        return "not_found"
    except Exception:
        return "error"


def delete_row_from_sheet(tab_name, col_name, target_val):
    # Compatibility helper for any existing call sites.
    return delete_row_status(tab_name, col_name, target_val) == "deleted"


def trip_exists_in_sheet(tab_name, trip_id):
    """
    Trả về True/False nếu đọc Sheet thành công; None nếu không thể đọc.
    Điều này ngăn app ghi trùng DATA khi Google Sheets đang lỗi hoặc timeout.
    """
    try:
        ws, records = get_worksheet_data(tab_name)
        if ws is None:
            return None
        target = str(trip_id).strip()
        return any(str(row.get("MÃ CUỐC XE", "")).strip() == target for row in records)
    except Exception:
        return None


def get_next_stt(tab_name):
    try:
        _, records = get_worksheet_data(tab_name)
        if not records:
            return 1
        values = []
        for row in records:
            try:
                values.append(int(float(str(row.get("STT", "")).strip())))
            except Exception:
                pass
        return max(values, default=0) + 1
    except Exception:
        return 1


def update_driver_status(phone, status_text):
    try:
        ws, records = get_worksheet_data("DANG_NHAP")
        if ws is None or not records:
            return False

        header = ws.row_values(1)
        col_idx = None
        for idx, value in enumerate(header, start=1):
            if str(value).strip().upper() == "HIỆN TRẠNG TÀI XẾ":
                col_idx = idx
                break

        if col_idx is None:
            col_idx = len(header) + 1
            ws.update_cell(1, col_idx, "HIỆN TRẠNG TÀI XẾ")

        target_phone = str(phone).strip()
        for row_index, row in enumerate(records, start=2):
            if str(row.get("SĐT", "")).strip() == target_phone:
                ws.update_cell(row_index, col_idx, status_text)
                return True
        return False
    except Exception:
        return False


def set_payment_method_in_sheet(tab_name, trip_id, payment_method):
    """Ghi phương thức thanh toán vào cột riêng; tự tạo cột nếu chưa tồn tại."""
    try:
        ws, records = get_worksheet_data(tab_name)
        if ws is None:
            return False

        header = ws.row_values(1)
        col_idx = None
        for idx, value in enumerate(header, start=1):
            if str(value).strip().upper() == "PHƯƠNG THỨC THANH TOÁN":
                col_idx = idx
                break

        if col_idx is None:
            col_idx = len(header) + 1
            ws.update_cell(1, col_idx, "PHƯƠNG THỨC THANH TOÁN")

        target = str(trip_id).strip()
        for row_index, row in enumerate(records, start=2):
            if str(row.get("MÃ CUỐC XE", "")).strip() == target:
                ws.update_cell(row_index, col_idx, payment_method)
                return True
        return False
    except Exception:
        return False


def get_active_cache_for_driver(driver_name):
    """Tìm cuốc chưa hoàn tất để hỗ trợ khôi phục sau refresh/mất phiên."""
    try:
        _, records = get_worksheet_data("CACHE_4567")
        if not records:
            return None

        candidates = []
        target_driver = str(driver_name).strip()
        for row in records:
            status = str(row.get("TRẠNG THÁI", "")).strip().upper()
            row_driver = str(row.get("TÊN TÀI XẾ", "")).strip()
            end_time = str(row.get("GIỜ KẾT THÚC", "")).strip()
            trip_id = str(row.get("MÃ CUỐC XE", "")).strip()
            if (
                row_driver == target_driver
                and status in {"BẮT ĐẦU CUỐC", "ĐANG CHẠY XE"}
                and end_time in {"", "---"}
                and trip_id
            ):
                candidates.append(row)

        if not candidates:
            return None

        _, data_records = get_worksheet_data("DATA_4567")
        completed_ids = {
            str(row.get("MÃ CUỐC XE", "")).strip()
            for row in data_records
            if str(row.get("MÃ CUỐC XE", "")).strip()
        }

        for row in reversed(candidates):
            trip_id = str(row.get("MÃ CUỐC XE", "")).strip()
            if trip_id not in completed_ids:
                return row
        return None
    except Exception:
        return None


def get_trip_start_timestamp(trip_id, fallback=None):
    try:
        return float(str(trip_id).rsplit("_", 1)[-1])
    except (ValueError, TypeError):
        return fallback if fallback is not None else time.time()


# ============================================================
# BẢNG GIÁ
# ============================================================
def get_pricing_tiers():
    _, records = get_worksheet_data("BANG_GIA")
    tiers = []
    for row in records:
        try:
            from_km = float(row.get("TỪ KM", 0))
            to_km = float(row.get("ĐẾN KM", 999999))
            price = float(row.get("ĐƠN GIÁ", 0))
            desc = str(row.get("MÔ TẢ", f"{price:,.0f} đ/km"))
            tiers.append({"from": from_km, "to": to_km, "price": price, "desc": desc})
        except Exception:
            continue

    if not tiers:
        tiers = [
            {"from": 0.0, "to": 3.0, "price": 0, "desc": "0 đ/km (Miễn phí < 3km)"},
            {"from": 3.0, "to": 11.0, "price": 4500, "desc": "4,500 đ/km (3km - dưới 11km)"},
            {"from": 11.0, "to": 40.0, "price": 4000, "desc": "4,000 đ/km (11km - dưới 40km)"},
            {"from": 40.0, "to": 999999.0, "price": 5500, "desc": "5,500 đ/km (Từ 40km trở lên)"},
        ]

    tiers.sort(key=lambda item: (item["from"], item["to"]))
    return tiers


def calculate_fare(km):
    km = max(0.0, float(km))
    for tier in get_pricing_tiers():
        if tier["from"] <= km < tier["to"]:
            return round(km * tier["price"])
    tiers = get_pricing_tiers()
    return round(km * tiers[-1]["price"]) if tiers else 0


def get_current_unit_price_desc(km):
    km = max(0.0, float(km))
    tiers = get_pricing_tiers()
    for tier in tiers:
        if tier["from"] <= km < tier["to"]:
            return tier["desc"]
    return tiers[-1]["desc"] if tiers else "Đơn giá chưa xác định"


# ============================================================
# CSS
# ============================================================
st.markdown(
    """
    <style>
    .stApp { background-color: #f1f5f9; }
    .block-container { max-width: 550px; padding: 1.0rem 1rem 2rem 1rem; }
    .pro-card {
        background: #ffffff;
        border-radius: 20px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 10px 25px -5px rgba(0,0,0,.05), 0 8px 10px -6px rgba(0,0,0,.05);
        border: 1px solid #e2e8f0;
    }
    .driver-header {
        background: linear-gradient(135deg, #059669 0%, #047857 100%);
        padding: 16px 20px;
        border-radius: 20px;
        color: white;
        margin-bottom: 14px;
        box-shadow: 0 10px 20px rgba(5,150,105,.2);
    }
    .driver-name { font-size: 20px; font-weight: 800; margin: 0; color: white; }
    .driver-phone { font-size: 14px; margin-top: 4px; color: #d1fae5; font-weight: 600; }
    div.stButton > button {
        border-radius: 16px !important;
        font-weight: 800 !important;
        font-size: 17px !important;
        min-height: 54px !important;
        background-color: #059669 !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 8px 20px rgba(5,150,105,.25);
    }
    input { font-size: 16px !important; font-weight: 600 !important; border-radius: 12px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================
defaults = {
    "step": 1,
    "user_phone": "",
    "user_name": "",
    "cust_name": "",
    "cust_phone": "",
    "trip_id": "",
    "trip_started_at": None,
    "final_end_ts": None,
    "final_dist": 0.0,
    "final_elapsed_seconds": 0,
    "gps_valid_points": 0,
    "trip_active_state": False,
    "saved_to_sheet": False,
    "payment_pending": False,
    "payment_method": "",
    "payment_confirmed": False,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# NHẬN TÍN HIỆU CHỐT CUỐC TỪ GPS COMPONENT
# ============================================================
if st.query_params.get("action") == "checkout":
    try:
        final_dist = max(0.0, float(st.query_params.get("dist", 0)))
    except (TypeError, ValueError):
        final_dist = 0.0

    try:
        start_ts = float(st.query_params.get("start", time.time()))
    except (TypeError, ValueError):
        start_ts = time.time()

    try:
        elapsed_seconds = max(0, int(float(st.query_params.get("elapsed", 0))))
    except (TypeError, ValueError):
        elapsed_seconds = 0

    try:
        gps_points = max(0, int(float(st.query_params.get("gps", 0))))
    except (TypeError, ValueError):
        gps_points = 0

    st.session_state["final_dist"] = final_dist
    st.session_state["trip_started_at"] = start_ts
    try:
        end_ts = float(st.query_params.get("ended", time.time()))
    except (TypeError, ValueError):
        end_ts = time.time()
    st.session_state["final_end_ts"] = end_ts
    st.session_state["final_elapsed_seconds"] = elapsed_seconds
    st.session_state["gps_valid_points"] = gps_points
    st.session_state["cust_name"] = st.query_params.get("cname", "Khách vãng lai") or "Khách vãng lai"
    st.session_state["cust_phone"] = st.query_params.get("cphone", "") or ""
    st.session_state["trip_id"] = f"C4567_{int(start_ts)}"
    st.session_state["payment_pending"] = True
    st.session_state["payment_confirmed"] = False
    st.session_state["payment_method"] = ""
    st.session_state["saved_to_sheet"] = False
    st.session_state["trip_active_state"] = True
    st.query_params.clear()
    st.session_state["step"] = 3
    st.rerun()


# ============================================================
# MÀN HÌNH ĐĂNG NHẬP
# ============================================================
if st.session_state["step"] == 1:
    st.markdown(
        """
        <div class="pro-card" style="text-align:center; padding:24px 20px; margin-top:10px;">
            <div style="font-size:42px;">🛵</div>
            <div style="font-size:22px; font-weight:900; color:#0f172a;">4567 XE ÔM</div>
            <div style="font-size:13px; color:#64748b; font-weight:600; margin-top:3px;">Đơn giản • Trực quan • Chính xác</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    phone_input = st.text_input("Số điện thoại tài xế:", placeholder="Nhập SĐT của bác...")
    if st.button("ĐĂNG NHẬP HỆ THỐNG", use_container_width=True):
        if not phone_input.strip():
            st.warning("⚠️ Bác vui lòng nhập số điện thoại.")
        else:
            with st.spinner("Đang xác thực thông tin..."):
                _, login_records = get_worksheet_data("DANG_NHAP")
                matched_user = next(
                    (row for row in login_records if str(row.get("SĐT", "")).strip() == phone_input.strip()),
                    None,
                )

            if matched_user:
                st.session_state["user_phone"] = str(matched_user.get("SĐT", ""))
                st.session_state["user_name"] = str(matched_user.get("TÊN TÀI XẾ", "Tài xế"))

                active_cache = get_active_cache_for_driver(st.session_state["user_name"])
                if active_cache:
                    trip_id = str(active_cache.get("MÃ CUỐC XE", "")).strip()
                    st.session_state["trip_id"] = trip_id
                    st.session_state["trip_started_at"] = get_trip_start_timestamp(trip_id)
                    st.session_state["cust_name"] = str(active_cache.get("TÊN KHÁCH HÀNG", "")).strip() or "Khách vãng lai"
                    st.session_state["cust_phone"] = str(active_cache.get("SĐT KHÁCH HÀNG", "")).strip()
                    st.session_state["trip_active_state"] = True
                    st.session_state["step"] = 2
                    update_driver_status(st.session_state["user_phone"], "Đang chạy xe")
                    st.info("🔄 Đã khôi phục cuốc đang chạy từ CACHE_4567.")
                else:
                    st.session_state["step"] = 2
                    update_driver_status(st.session_state["user_phone"], "Trực tuyến")
                    st.success(f"Chào bác **{st.session_state['user_name']}**!")
                time.sleep(0.3)
                st.rerun()
            else:
                st.error("❌ Số điện thoại không đúng hoặc chưa được cấp quyền.")
    st.stop()


# ============================================================
# HEADER
# ============================================================
st.markdown(
    f"""
    <div class="driver-header">
        <div class="driver-name">👨‍✈️ Tài xế: {safe_html(st.session_state['user_name'])}</div>
        <div class="driver-phone">📞 SĐT: {safe_html(st.session_state['user_phone'])}</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# MÀN HÌNH 2 — KHỞI TẠO CUỐC + GPS
# ============================================================
if st.session_state["step"] == 2:
    if not st.session_state["trip_active_state"]:
        st.markdown(
            """
            <div class="pro-card">
                <div style="font-size:15px; font-weight:800; color:#0f172a; margin-bottom:10px;">📝 KHỞI TẠO CUỐC XE</div>
            """,
            unsafe_allow_html=True,
        )
        cust_name_in = st.text_input("Tên khách hàng (Tùy chọn):", placeholder="VD: Anh Nam")
        cust_phone_in = st.text_input("SĐT khách hàng (Tùy chọn):", placeholder="VD: 0912345678")
        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("🟢 BẮT ĐẦU HÀNH TRÌNH", use_container_width=True):
            started_at = time.time()
            trip_id = f"C4567_{int(started_at)}"
            cust_name = cust_name_in.strip() or "Khách vãng lai"
            cust_phone = cust_phone_in.strip()

            cache_row = [
                get_next_stt("CACHE_4567"),
                trip_id,
                get_vn_time(started_at),
                "---",
                "---",
                cust_name,
                cust_phone,
                0,
                st.session_state["user_name"],
                "---",
                0,
                0,
                "BẮT ĐẦU CUỐC",
            ]

            if append_row_to_sheet("CACHE_4567", cache_row):
                st.session_state["trip_id"] = trip_id
                st.session_state["trip_started_at"] = started_at
                st.session_state["cust_name"] = cust_name
                st.session_state["cust_phone"] = cust_phone
                st.session_state["trip_active_state"] = True
                st.session_state["saved_to_sheet"] = False
                st.session_state["payment_pending"] = False
                st.session_state["payment_confirmed"] = False
                st.session_state["payment_method"] = ""
                st.session_state["final_elapsed_seconds"] = 0
                st.session_state["gps_valid_points"] = 0
                update_driver_status(st.session_state["user_phone"], "Đang chạy xe")
                st.rerun()
            else:
                st.error("❌ Không thể ghi CACHE_4567. Vui lòng kiểm tra kết nối Google Sheets.")

    else:
        current_start_ts = st.session_state.get("trip_started_at") or time.time()
        cname_val = st.session_state.get("cust_name", "Khách vãng lai")
        cphone_val = st.session_state.get("cust_phone", "")
        trip_id_js = json.dumps(st.session_state["trip_id"], ensure_ascii=False)
        customer_name_js = json.dumps(cname_val, ensure_ascii=False)
        customer_phone_js = json.dumps(cphone_val, ensure_ascii=False)
        tiers_json = json.dumps(get_pricing_tiers(), ensure_ascii=False)

        st.markdown(
            f"""
            <div class="pro-card" style="border-left:5px solid #059669; background:#f8fafc;">
                <div style="color:#059669; font-size:12px; font-weight:800; text-transform:uppercase;">🟢 ĐANG ĐO HÀNH TRÌNH GPS</div>
                <div style="font-size:14px; color:#1e293b; margin-top:4px; font-weight:700;">Khách: {safe_html(cname_val)} &bull; SĐT: {safe_html(cphone_val)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tracker_html = f"""
        <div style="font-family:system-ui,-apple-system,sans-serif;padding:2px;">
            <style>
                .action-btn {{
                    border:none; border-radius:16px; padding:14px; font-size:15px; font-weight:900;
                    cursor:pointer; min-height:58px;
                }}
                .action-btn:active {{ transform:scale(.97); }}
            </style>

            <div id="toast" style="visibility:hidden; opacity:0; position:relative; background:#0f172a; color:#fff; text-align:center; border-radius:12px; padding:10px 14px; margin-bottom:8px; font-size:13px; font-weight:800; transition:opacity .2s;">Thông báo</div>

            <div style="background:linear-gradient(135deg,#064e3b 0%,#022c22 100%); border-radius:20px; padding:20px 16px; text-align:center; box-shadow:0 10px 25px rgba(2,44,34,.2);">
                <div id="status" style="color:#34d399;font-size:12px;font-weight:900;text-transform:uppercase;letter-spacing:.6px;">🟢 ĐANG CHẠY GPS + ĐỒNG HỒ</div>
                <div id="price" style="color:#fff;font-size:40px;font-weight:900;margin:5px 0;">0 VNĐ</div>
                <div style="display:flex;justify-content:space-around;margin-top:12px;font-size:15px;font-weight:800;color:#e2e8f0;border-top:1px solid rgba(255,255,255,.12);padding-top:10px;">
                    <div>⏱ <span id="timer">00:00:00</span></div>
                    <div>🛣 <span id="km">0.000</span> km</div>
                </div>
                <div id="rate" style="color:#a7f3d0;font-size:12px;margin-top:8px;font-weight:700;">Đơn giá: Đang tải...</div>
            </div>

            <div style="display:flex;gap:10px;margin-top:10px;">
                <button id="pauseBtn" class="action-btn" type="button" onclick="togglePause()" style="flex:1;background:#d97706;color:#fff;">⏸ TẠM DỪNG</button>
                <form id="checkoutForm" method="get" action="/" target="_top" onsubmit="return prepareCheckout(event)" style="flex:1.2;margin:0;">
                    <input type="hidden" name="action" value="checkout">
                    <input type="hidden" name="dist" id="checkoutDist">
                    <input type="hidden" name="start" id="checkoutStart">
                    <input type="hidden" name="elapsed" id="checkoutElapsed">
                    <input type="hidden" name="gps" id="checkoutGps">
                    <input type="hidden" name="ended" id="checkoutEnded">
                    <input type="hidden" name="cname" id="checkoutCname">
                    <input type="hidden" name="cphone" id="checkoutCphone">
                    <button id="payBtn" class="action-btn" type="submit" style="width:100%;background:#059669;color:#fff;">💵 THANH TOÁN</button>
                </form>
            </div>

            <div id="gps" style="text-align:center;font-size:12px;color:#64748b;font-weight:700;margin-top:8px;">📡 GPS: Đang bắt tín hiệu...</div>
        </div>

        <script>
        const tripStorageKey = "xeom_4567_" + {trip_id_js};
        const startTimestamp = {current_start_ts};
        const customerName = {customer_name_js};
        const customerPhone = {customer_phone_js};
        const pricingTiers = {tiers_json};

        let isPaused = localStorage.getItem(tripStorageKey + ":paused") === "1";
        let totalMeters = parseFloat(localStorage.getItem(tripStorageKey + ":meters") || "0");
        let elapsedSeconds = parseInt(localStorage.getItem(tripStorageKey + ":seconds") || "0", 10);
        let validGpsPoints = parseInt(localStorage.getItem(tripStorageKey + ":gps") || "0", 10);
        let lastClockMs = parseInt(localStorage.getItem(tripStorageKey + ":clock") || "0", 10);
        let lastLat = parseFloat(localStorage.getItem(tripStorageKey + ":lat") || "NaN");
        let lastLon = parseFloat(localStorage.getItem(tripStorageKey + ":lon") || "NaN");

        if (!Number.isFinite(totalMeters) || totalMeters < 0) totalMeters = 0;
        if (!Number.isFinite(elapsedSeconds) || elapsedSeconds < 0) elapsedSeconds = 0;
        if (!Number.isFinite(validGpsPoints) || validGpsPoints < 0) validGpsPoints = 0;
        if (!Number.isFinite(lastClockMs) || lastClockMs <= 0) lastClockMs = Date.now();

        function vibrate(ms) {{ if (navigator.vibrate) navigator.vibrate(ms); }}

        function toast(text, background="#0f172a") {{
            const box = document.getElementById("toast");
            box.innerText = text; box.style.background = background;
            box.style.visibility = "visible"; box.style.opacity = "1";
            clearTimeout(window.__toastTimer);
            window.__toastTimer = setTimeout(() => {{ box.style.opacity = "0"; box.style.visibility = "hidden"; }}, 2200);
        }}

        function fareForKm(km) {{
            for (const t of pricingTiers) if (km >= t.from && km < t.to) return Math.round(km * t.price);
            return pricingTiers.length ? Math.round(km * pricingTiers[pricingTiers.length - 1].price) : 0;
        }}

        function rateForKm(km) {{
            for (const t of pricingTiers) if (km >= t.from && km < t.to) return t.desc;
            return pricingTiers.length ? pricingTiers[pricingTiers.length - 1].desc : "Đơn giá chưa xác định";
        }}

        function render() {{
            const h = Math.floor(elapsedSeconds / 3600);
            const m = Math.floor((elapsedSeconds % 3600) / 60);
            const s = elapsedSeconds % 60;
            document.getElementById("timer").innerText =
                String(h).padStart(2,"0") + ":" + String(m).padStart(2,"0") + ":" + String(s).padStart(2,"0");
            const km = totalMeters / 1000;
            document.getElementById("km").innerText = km.toFixed(3);
            document.getElementById("price").innerText = fareForKm(km).toLocaleString("vi-VN") + " VNĐ";
            document.getElementById("rate").innerText = "Đơn giá: " + rateForKm(km);
        }}

        function persist() {{
            localStorage.setItem(tripStorageKey + ":paused", isPaused ? "1" : "0");
            localStorage.setItem(tripStorageKey + ":meters", String(totalMeters));
            localStorage.setItem(tripStorageKey + ":seconds", String(elapsedSeconds));
            localStorage.setItem(tripStorageKey + ":gps", String(validGpsPoints));
            localStorage.setItem(tripStorageKey + ":clock", String(lastClockMs));
            if (Number.isFinite(lastLat) && Number.isFinite(lastLon)) {{
                localStorage.setItem(tripStorageKey + ":lat", String(lastLat));
                localStorage.setItem(tripStorageKey + ":lon", String(lastLon));
            }}
        }}

        function syncClock() {{
            const now = Date.now();
            if (!isPaused) {{
                const delta = Math.max(0, now - lastClockMs);
                elapsedSeconds += Math.floor(delta / 1000);
                lastClockMs += Math.floor(delta / 1000) * 1000;
            }} else {{
                lastClockMs = now;
            }}
            persist(); render();
        }}

        function paintPauseState() {{
            const btn = document.getElementById("pauseBtn");
            const status = document.getElementById("status");
            if (isPaused) {{
                btn.innerText = "▶️ TIẾP TỤC";
                btn.style.background = "#2563eb";
                status.innerText = "⏸ ĐANG TẠM DỪNG GPS + ĐỒNG HỒ";
                status.style.color = "#fbbf24";
            }} else {{
                btn.innerText = "⏸ TẠM DỪNG";
                btn.style.background = "#d97706";
                status.innerText = "🟢 ĐANG CHẠY GPS + ĐỒNG HỒ";
                status.style.color = "#34d399";
            }}
        }}

        function togglePause() {{
            vibrate(60);
            syncClock();
            isPaused = !isPaused;
            lastClockMs = Date.now();
            persist(); paintPauseState();
            toast(isPaused ? "⏸ Đã tạm dừng GPS và đồng hồ." : "▶️ Đã tiếp tục GPS và đồng hồ.", isPaused ? "#d97706" : "#059669");
        }}

        function distanceMeters(lat1, lon1, lat2, lon2) {{
            const R = 6371000;
            const dLat = (lat2-lat1) * Math.PI / 180;
            const dLon = (lon2-lon1) * Math.PI / 180;
            const a = Math.sin(dLat/2)**2 + Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2;
            return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        }}

        render(); paintPauseState(); syncClock();
        setInterval(syncClock, 500);

        if ("geolocation" in navigator) {{
            navigator.geolocation.watchPosition(
                pos => {{
                    const lat = pos.coords.latitude;
                    const lon = pos.coords.longitude;
                    const acc = Number(pos.coords.accuracy);
                    const speed = Number.isFinite(pos.coords.speed) ? pos.coords.speed : null;
                    const gpsBox = document.getElementById("gps");

                    if (!Number.isFinite(acc)) {{
                        gpsBox.innerText = "⚠️ GPS không đọc được độ chính xác.";
                        return;
                    }}
                    if (acc > {GPS_ACCURACY_MAX_M}) {{
                        gpsBox.innerText = "⚠️ GPS yếu: ±" + acc.toFixed(1) + "m — chưa cộng KM";
                        return;
                    }}

                    validGpsPoints++;
                    gpsBox.innerText = "✅ GPS hợp lệ: ±" + acc.toFixed(1) + "m";

                    if (!Number.isFinite(lastLat) || !Number.isFinite(lastLon)) {{
                        lastLat = lat; lastLon = lon; persist(); return;
                    }}

                    const d = distanceMeters(lastLat, lastLon, lat, lon);
                    const speedInvalid = speed !== null && speed > {MAX_SPEED_MPS};

                    if (!isPaused && !speedInvalid && d >= {MIN_MOVE_M} && d <= {MAX_SEGMENT_M}) {{
                        totalMeters += d;
                        persist(); render();
                    }}

                    if (!speedInvalid && d <= {MAX_SEGMENT_M}) {{
                        lastLat = lat; lastLon = lon;
                        persist();
                    }}
                }},
                err => {{
                    document.getElementById("gps").innerText = "❌ GPS lỗi: Hãy bật Định vị trên điện thoại.";
                }},
                {{ enableHighAccuracy:true, maximumAge:1000, timeout:15000 }}
            );
        }} else {{
            document.getElementById("gps").innerText = "❌ Thiết bị không hỗ trợ GPS.";
        }}

        let paymentNavigating = false;

        function prepareCheckout(event) {{
            if (paymentNavigating) {{
                event.preventDefault();
                return false;
            }}

            vibrate(90);
            syncClock();
            persist();
            paymentNavigating = true;

            // Dùng form HTML native + target="_top".
            // Không dùng window.parent/window.top.location/document.referrer.
            // Vì đây là điều hướng do chính thao tác bấm nút của người dùng,
            // trình duyệt sẽ đưa trang checkout lên đúng tab hiện tại, không lồng App.
            document.getElementById("checkoutDist").value = String(totalMeters);
            document.getElementById("checkoutStart").value = String(startTimestamp);
            document.getElementById("checkoutElapsed").value = String(elapsedSeconds);
            document.getElementById("checkoutGps").value = String(validGpsPoints);
            document.getElementById("checkoutEnded").value = String(Date.now() / 1000);
            document.getElementById("checkoutCname").value = customerName;
            document.getElementById("checkoutCphone").value = customerPhone;

            const payBtn = document.getElementById("payBtn");
            if (payBtn) {{
                payBtn.disabled = true;
                payBtn.style.opacity = "0.7";
                payBtn.innerText = "⏳ ĐANG MỞ THANH TOÁN...";
            }}

            toast("Đang mở xác nhận thanh toán...", "#059669");
            return true;
        }}
        </script>
        """
        components.html(tracker_html, height=370)


# ============================================================
# MÀN HÌNH 3 — XÁC NHẬN THANH TOÁN + HÓA ĐƠN
# ============================================================
elif st.session_state["step"] == 3:
    start_ts = st.session_state.get("trip_started_at") or time.time()
    end_ts = st.session_state.get("final_end_ts") or time.time()
    dist_val = max(0.0, float(st.session_state.get("final_dist", 0.0)))
    elapsed_seconds = max(0, int(st.session_state.get("final_elapsed_seconds", 0)))
    cname = st.session_state.get("cust_name", "Khách vãng lai")
    cphone = st.session_state.get("cust_phone", "")
    trip_id = st.session_state.get("trip_id", "")
    gps_points = int(st.session_state.get("gps_valid_points", 0))

    start_time_str = get_vn_time(start_ts)
    end_time_str = get_vn_time(end_ts)
    hh, mm, ss = elapsed_seconds // 3600, (elapsed_seconds % 3600) // 60, elapsed_seconds % 60
    total_time_str = f"{hh:02d}:{mm:02d}:{ss:02d}"
    km_exact = dist_val / 1000.0
    fare_val = calculate_fare(km_exact)
    unit_desc = get_current_unit_price_desc(km_exact)
    driver_name_val = st.session_state.get("user_name", "Tài xế")

    if st.session_state.get("payment_pending", False):
        st.markdown(
            f"""
            <div class="pro-card" style="border:2px solid #059669; background:linear-gradient(180deg,#fff 0%,#f0fdf4 100%);">
                <div style="text-align:center;">
                    <div style="font-size:38px;">💵</div>
                    <div style="font-size:22px; font-weight:900; color:#064e3b;">XÁC NHẬN THANH TOÁN</div>
                    <div style="font-size:13px; color:#64748b; font-weight:700; margin-top:3px;">Mã cuốc: {safe_html(trip_id)}</div>
                </div>
                <div style="margin-top:14px;background:#fff;border-radius:16px;padding:14px;border:1px solid #d1fae5;">
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px;"><span style="color:#64748b;">Khách hàng</span><b>{safe_html(cname)}</b></div>
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px;"><span style="color:#64748b;">Quãng đường GPS</span><b>{km_exact:.3f} km</b></div>
                    <div style="display:flex;justify-content:space-between;margin-bottom:8px;"><span style="color:#64748b;">Thời gian đi</span><b>{total_time_str}</b></div>
                    <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">GPS hợp lệ</span><b>{gps_points} điểm</b></div>
                </div>
                <div style="text-align:center;margin-top:15px;">
                    <div style="font-size:12px;color:#64748b;font-weight:800;text-transform:uppercase;">SỐ TIỀN KHÁCH CẦN THANH TOÁN</div>
                    <div style="font-size:40px;font-weight:900;color:#059669;margin-top:2px;">{format(fare_val, ',')} VNĐ</div>
                    <div style="font-size:12px;color:#64748b;font-weight:700;margin-top:4px;">{safe_html(unit_desc)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        payment_method = st.radio(
            "CHỌN PHƯƠNG THỨC THANH TOÁN",
            ["💵 TIỀN MẶT", "🏦 CHUYỂN KHOẢN"],
            index=0,
            key="payment_method_selector",
        )
        st.session_state["payment_method"] = "Tiền mặt" if payment_method.startswith("💵") else "Chuyển khoản"

        if gps_points <= 0:
            st.warning("⚠️ Chưa có điểm GPS hợp lệ. Hãy kiểm tra định vị trước khi xác nhận thanh toán để tránh tính sai quãng đường.")
        else:
            st.info("ℹ️ Chỉ bấm xác nhận sau khi bác đã thực nhận đủ tiền từ khách.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("↩️ QUAY LẠI", use_container_width=True):
                st.session_state["payment_pending"] = False
                st.session_state["step"] = 2
                st.rerun()
        with col2:
            if st.button("✅ XÁC NHẬN ĐÃ NHẬN TIỀN", use_container_width=True):
                st.session_state["payment_confirmed"] = True
                st.session_state["payment_pending"] = False
                st.rerun()

        st.stop()

    # --------------------------------------------------------
    # GHI DATA — CHỈ SAU KHI ĐÃ XÁC NHẬN NHẬN TIỀN
    # --------------------------------------------------------
    payment_method = st.session_state.get("payment_method") or "Tiền mặt"
    if st.session_state.get("payment_confirmed", False) and not st.session_state["saved_to_sheet"]:
        data_exists = trip_exists_in_sheet("DATA_4567", trip_id)
        data_saved = False

        if data_exists is None:
            st.error("❌ Không đọc được DATA_4567. Chưa chốt giao dịch để tránh ghi trùng.")
        elif data_exists:
            data_saved = True
        else:
            row_data = [
                get_next_stt("DATA_4567"),
                trip_id,
                start_time_str,
                end_time_str,
                total_time_str,
                cname,
                cphone,
                fare_val,
                driver_name_val,
                unit_desc,
                km_exact,
                fare_val,
                "ĐÃ THANH TOÁN",
            ]
            data_saved = append_row_to_sheet("DATA_4567", row_data)

        if data_saved:
            method_saved = set_payment_method_in_sheet("DATA_4567", trip_id, payment_method)
            if method_saved:
                # DATA + phương thức đã ổn; chỉ khi CACHE được xóa (hoặc đã không còn)
                # mới coi giao dịch là hoàn tất.
                cache_status = delete_row_status("CACHE_4567", "MÃ CUỐC XE", trip_id)
                if cache_status in {"deleted", "not_found"}:
                    st.session_state["saved_to_sheet"] = True
                else:
                    st.error("⚠️ DATA_4567 đã lưu an toàn nhưng CACHE_4567 chưa xóa được. Giữ nguyên màn hình để thử lại.")
            else:
                st.error("❌ DATA_4567 đã có nhưng chưa ghi được phương thức thanh toán. Giữ nguyên màn hình để thử lại.")
        elif data_exists is not None:
            st.error("❌ Chưa thể lưu hóa đơn vào DATA_4567. Vui lòng giữ nguyên màn hình và thử lại.")

    if st.session_state["saved_to_sheet"]:
        st.success(f"✅ Đã xác nhận thanh toán bằng **{payment_method}** và đồng bộ dữ liệu.")

    # --------------------------------------------------------
    # HÓA ĐƠN — CÙNG MỘT TRANG, KHÔNG NHÚNG STREAMLIT VÀO STREAMLIT
    # --------------------------------------------------------
    st.markdown(
        f"""
        <div class="pro-card" style="border:2px solid #059669;">
            <div style="text-align:center;border-bottom:2px dashed #cbd5e1;padding-bottom:12px;margin-bottom:12px;">
                <div style="font-size:32px;">🧾</div>
                <div style="font-size:19px;font-weight:900;color:#064e3b;">HÓA ĐƠN CHI TIẾT CHUYẾN ĐI</div>
                <div style="font-size:12px;color:#64748b;font-weight:700;">Mã cuốc: {safe_html(trip_id)}</div>
            </div>
            <div style="font-size:14px;color:#334155;line-height:1.8;">
                <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">Khách hàng:</span><b>{safe_html(cname)} ({safe_html(cphone) if cphone else 'Không có SĐT'})</b></div>
                <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">Tài xế:</span><b>{safe_html(driver_name_val)}</b></div>
                <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">Giờ khởi hành:</span><b>{start_time_str}</b></div>
                <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">Giờ kết thúc:</span><b>{end_time_str}</b></div>
                <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">Thời gian đi:</span><b>{total_time_str}</b></div>
                <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">Quãng đường GPS:</span><b style="color:#059669;">{km_exact:.3f} km</b></div>
                <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">Mức giá:</span><b style="color:#d97706;">{safe_html(unit_desc)}</b></div>
                <div style="display:flex;justify-content:space-between;"><span style="color:#64748b;">Thanh toán:</span><b style="color:#059669;">{safe_html(payment_method)}</b></div>
            </div>
            <div style="margin-top:14px;padding-top:12px;border-top:2px dashed #cbd5e1;text-align:center;">
                <div style="font-size:12px;color:#64748b;font-weight:800;text-transform:uppercase;">TỔNG THÀNH TIỀN</div>
                <div style="font-size:36px;font-weight:900;color:#059669;margin-top:2px;">{format(fare_val, ',')} VNĐ</div>
                <div style="font-size:11px;color:#10b981;font-weight:700;margin-top:3px;">✅ Đã xác nhận và đồng bộ Google Sheets</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("⬅️ QUAY LẠI MÀN HÌNH CHÍNH", use_container_width=True):
        update_driver_status(st.session_state["user_phone"], "Trực tuyến")
        st.session_state["trip_active_state"] = False
        st.session_state["saved_to_sheet"] = False
        st.session_state["payment_pending"] = False
        st.session_state["payment_confirmed"] = False
        st.session_state["payment_method"] = ""
        st.session_state["final_dist"] = 0.0
        st.session_state["final_elapsed_seconds"] = 0
        st.session_state["gps_valid_points"] = 0
        st.session_state["trip_id"] = ""
        st.session_state["step"] = 2
        st.rerun()
