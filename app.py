import datetime
import math
import time
import html
import gspread
import pytz
import streamlit as st
import streamlit.components.v1 as components
from google.oauth2.service_account import Credentials

# ============================================================
# 4567 XE ÔM — BẢN ỔN ĐỊNH / 1 TRANG / CACHE -> DATA
# ============================================================

st.set_page_config(
    page_title="4567 Xe Ôm",
    page_icon="🛵",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# -------------------- CẤU HÌNH --------------------
DONG_GIA = 5000
GPS_ACCURACY_MAX_M = 60
MIN_MOVE_M = 4

SHEET_KEY = st.secrets["connections"]["gsheets"].get(
    "spreadsheet",
    "1A3-1am25vZLN57SD7pkfxxQtymCaPnCj9HgBpw5RcTY",
)

# -------------------- THỜI GIAN --------------------
def get_vn_time(timestamp=None):
    vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
    if timestamp is None:
        return datetime.datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")
    return datetime.datetime.fromtimestamp(timestamp, vn_tz).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# -------------------- GOOGLE SHEETS --------------------
@st.cache_resource
def init_google_sheet_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = dict(st.secrets["connections"]["gsheets"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)


def get_sheet(tab_name):
    try:
        client = init_google_sheet_client()
        return client.open_by_key(SHEET_KEY).worksheet(tab_name)
    except Exception:
        return None


def get_worksheet_data(tab_name):
    try:
        ws = get_sheet(tab_name)
        if not ws:
            return None, []
        return ws, ws.get_all_records()
    except Exception:
        return None, []


def get_headers(tab_name):
    ws = get_sheet(tab_name)
    if not ws:
        return []
    try:
        return ws.row_values(1)
    except Exception:
        return []


def get_next_stt(tab_name):
    try:
        _, records = get_worksheet_data(tab_name)
        return len(records) + 1 if records else 1
    except Exception:
        return 1


def append_row_to_sheet(tab_name, row_values):
    try:
        ws = get_sheet(tab_name)
        if not ws:
            return False
        ws.append_row(row_values, value_input_option="USER_ENTERED")
        return True
    except Exception:
        return False


def delete_row_from_sheet(tab_name, col_name, target_val):
    try:
        ws, records = get_worksheet_data(tab_name)
        if not ws:
            return False
        for i, row in enumerate(records, start=2):
            if str(row.get(col_name, "")).strip() == str(target_val).strip():
                ws.delete_rows(i)
                return True
    except Exception:
        pass
    return False


def update_driver_status(phone, status):
    if phone == "KHÁCH HÀNG":
        return
    try:
        ws, records = get_worksheet_data("DANG_NHAP")
        if not ws:
            return

        headers = ws.row_values(1)
        if "HIỆN TRẠNG TÀI XẾ" not in headers:
            return

        col_idx = headers.index("HIỆN TRẠNG TÀI XẾ") + 1
        for i, row in enumerate(records, start=2):
            if str(row.get("SĐT", "")).strip() == str(phone).strip():
                ws.update_cell(i, col_idx, status)
                break
    except Exception:
        pass


# ============================================================
# GHI DỮ LIỆU THEO ĐÚNG TIÊU ĐỀ SHEET
# Không phụ thuộc thứ tự cột. Dữ liệu được ráp theo tên tiêu đề.
# ============================================================
HEADER_ALIASES = {
    "STT": ["STT", "SỐ TT", "SỐ THỨ TỰ"],
    "MÃ CUỐC XE": ["MÃ CUỐC XE", "MA CUOC XE", "MÃ CHUYẾN", "MÃ CUỐC"],
    "THỜI GIAN BẮT ĐẦU": [
        "THỜI GIAN BẮT ĐẦU",
        "THỜI GIAN BẮT ĐẦU CUỐC",
        "THỜI GIAN NHẬN",
        "BẮT ĐẦU",
    ],
    "THỜI GIAN KẾT THÚC": [
        "THỜI GIAN KẾT THÚC",
        "THỜI GIAN KẾT THÚC CUỐC",
        "THỜI GIAN TRẢ KHÁCH",
        "KẾT THÚC",
    ],
    "TỔNG THỜI GIAN": ["TỔNG THỜI GIAN", "THỜI GIAN CHẠY", "THỜI LƯỢNG"],
    "TÊN KHÁCH HÀNG": ["TÊN KHÁCH HÀNG", "KHÁCH HÀNG", "TÊN KHÁCH"],
    "SĐT KHÁCH HÀNG": [
        "SĐT KHÁCH HÀNG",
        "SĐT KHÁCH",
        "ĐIỆN THOẠI KHÁCH",
        "SĐT KH",
    ],
    "CƯỚC PHÍ": ["CƯỚC PHÍ", "TIỀN CƯỚC", "THÀNH TIỀN"],
    "TÊN TÀI XẾ": ["TÊN TÀI XẾ", "TÀI XẾ"],
    "ĐƠN GIÁ": ["ĐƠN GIÁ", "ĐƠN GIÁ/KM", "GIÁ/KM"],
    "QUÃNG ĐƯỜNG": ["QUÃNG ĐƯỜNG", "SỐ KM", "KM", "KHOẢNG CÁCH"],
    "TỔNG TIỀN": ["TỔNG TIỀN", "TIỀN", "TỔNG CƯỚC"],
    "TRẠNG THÁI": ["TRẠNG THÁI", "TÌNH TRẠNG", "TRẠNG THÁI CUỐC XE"],
}


def normalize_text(value):
    return " ".join(str(value or "").strip().upper().split())


def find_header_index(headers, aliases):
    normalized = {normalize_text(h): i for i, h in enumerate(headers)}
    for alias in aliases:
        if normalize_text(alias) in normalized:
            return normalized[normalize_text(alias)]
    return None


def build_sheet_row(tab_name, values):
    """
    values dùng tên chuẩn ở phía trên.
    Kết quả luôn theo đúng thứ tự tiêu đề thực tế của Sheet.
    """
    headers = get_headers(tab_name)
    if not headers:
        return None, "Không đọc được tiêu đề Sheet."

    row = [""] * len(headers)
    missing = []

    for canonical, value in values.items():
        aliases = HEADER_ALIASES.get(canonical, [canonical])
        idx = find_header_index(headers, aliases)
        if idx is not None:
            row[idx] = value

    # Các cột cốt lõi cần có để dữ liệu không bị ghi sai.
    required = ["MÃ CUỐC XE", "TÊN TÀI XẾ", "QUÃNG ĐƯỜNG"]
    for key in required:
        if find_header_index(headers, HEADER_ALIASES[key]) is None:
            missing.append(key)

    if missing:
        return None, "Thiếu tiêu đề cột: " + ", ".join(missing)

    return row, None


def save_trip_to_data(
    trip_id,
    start_ts,
    end_ts,
    total_time_str,
    cust_name,
    cust_phone,
    km_val,
    fare_val,
    driver_name,
    status,
):
    values = {
        "STT": get_next_stt("DATA_4567"),
        "MÃ CUỐC XE": trip_id,
        "THỜI GIAN BẮT ĐẦU": get_vn_time(start_ts),
        "THỜI GIAN KẾT THÚC": get_vn_time(end_ts),
        "TỔNG THỜI GIAN": total_time_str,
        "TÊN KHÁCH HÀNG": cust_name,
        "SĐT KHÁCH HÀNG": cust_phone,
        "CƯỚC PHÍ": fare_val,
        "TÊN TÀI XẾ": driver_name,
        "ĐƠN GIÁ": DONG_GIA,
        "QUÃNG ĐƯỜNG": km_val,
        "TỔNG TIỀN": fare_val,
        "TRẠNG THÁI": status,
    }

    row, error = build_sheet_row("DATA_4567", values)
    if row is None:
        return False, error

    ok = append_row_to_sheet("DATA_4567", row)
    return ok, None if ok else "Không thể ghi vào DATA_4567."


def save_trip_to_cache(trip_id, start_ts, cust_name, cust_phone, driver_name):
    values = {
        "STT": get_next_stt("CACHE_4567"),
        "MÃ CUỐC XE": trip_id,
        "THỜI GIAN BẮT ĐẦU": get_vn_time(start_ts),
        "THỜI GIAN KẾT THÚC": "---",
        "TỔNG THỜI GIAN": "---",
        "TÊN KHÁCH HÀNG": cust_name,
        "SĐT KHÁCH HÀNG": cust_phone,
        "CƯỚC PHÍ": 0,
        "TÊN TÀI XẾ": driver_name,
        "ĐƠN GIÁ": DONG_GIA,
        "QUÃNG ĐƯỜNG": 0,
        "TỔNG TIỀN": 0,
        "TRẠNG THÁI": "BẮT ĐẦU CUỐC",
    }

    row, error = build_sheet_row("CACHE_4567", values)
    if row is None:
        return False, error

    ok = append_row_to_sheet("CACHE_4567", row)
    return ok, None if ok else "Không thể ghi vào CACHE_4567."


# -------------------- CSS: 1 TRANG, GỌN, KHÔNG THANH TRẮNG --------------------
st.markdown(
    """
<style>
/* Ẩn các phần UI thừa của Streamlit */
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stToolbar"] {display:none;}
[data-testid="stDecoration"] {display:none;}
[data-testid="stStatusWidget"] {display:none;}

.stApp {
    background: #f1f5f9;
}

.block-container {
    max-width: 560px !important;
    padding: 0.35rem 0.65rem 0.65rem 0.65rem !important;
}

/* Giảm khoảng cách mặc định */
[data-testid="stVerticalBlock"] {
    gap: 0.45rem;
}

h1, h2, h3, h4, p {
    margin-top: 0 !important;
    margin-bottom: 0.35rem !important;
}

/* Nút lớn, dễ bấm */
div.stButton > button {
    min-height: 58px !important;
    border-radius: 13px !important;
    font-size: 21px !important;
    font-weight: 900 !important;
    padding: 8px 12px !important;
}

/* Ô nhập liệu dễ nhìn */
div[data-baseweb="input"] input {
    font-size: 19px !important;
    min-height: 48px !important;
}

label {
    font-size: 17px !important;
    font-weight: 800 !important;
}

/* Khung chính */
.action-box {
    background: #ffffff;
    border-radius: 16px;
    padding: 13px;
    border: 1px solid #d7dee8;
    box-shadow: 0 4px 12px rgba(15,23,42,.06);
}

/* Header App */
.app-title {
    text-align: center;
    color: #008f5a;
    font-size: 28px;
    font-weight: 950;
    line-height: 1.05;
    margin: 3px 0 2px 0;
}

.driver-line {
    text-align: center;
    color: #475569;
    font-size: 14px;
    margin-bottom: 5px;
}

/* Hướng dẫn tĩnh — không marquee, không chiếm chiều cao */
.help-line {
    background: #ecfdf5;
    color: #166534;
    border: 1px solid #bbf7d0;
    border-radius: 10px;
    padding: 8px 10px;
    text-align: center;
    font-size: 14px;
    font-weight: 750;
    margin-bottom: 8px;
}

/* Màn hình đang chạy */
.live-card {
    text-align: center;
    padding: 3px 2px 0 2px;
}

.live-label {
    color: #64748b;
    font-size: 15px;
    font-weight: 900;
}

.live-price {
    color: #059669;
    font-size: 43px;
    line-height: 1.05;
    font-weight: 950;
    margin: 4px 0;
}

.live-km {
    color: #0284c7;
    font-size: 21px;
    font-weight: 900;
}

.live-rate {
    color: #475569;
    font-size: 15px;
    font-weight: 700;
}

.gps-line {
    color: #64748b;
    font-size: 12px;
    margin-top: 7px;
}

/* Hóa đơn */
.receipt-box {
    border: 1px dashed #94a3b8;
    border-radius: 13px;
    padding: 13px;
    text-align: center;
    background: #fff;
}

.receipt-total {
    font-size: 30px;
    font-weight: 950;
    color: #059669;
    margin: 4px 0;
}

.small-btn a {
    text-decoration: none !important;
}

/* Giảm khoảng cách giữa các columns */
[data-testid="column"] {
    padding: 0 3px !important;
}

/* Trên điện thoại */
@media (max-width: 600px) {
    .block-container {
        padding: 0.25rem 0.45rem 0.45rem 0.45rem !important;
    }
    .app-title { font-size: 25px; }
    div.stButton > button {
        min-height: 54px !important;
        font-size: 19px !important;
    }
}
</style>
""",
    unsafe_allow_html=True,
)

# -------------------- SESSION STATE --------------------
defaults = {
    "logged_in": False,
    "user_phone": "",
    "user_name": "",
    "cust_name": "",
    "cust_phone": "",
    "trip_active": False,
    "trip_id": "",
    "trip_started_at": None,
    "trip_ended_at": None,
    "trip_total_m": 0.0,
    "login_success_effect": False,
    "end_trip_effect": False,
    "last_save_error": "",
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_trip():
    st.session_state.trip_active = False
    st.session_state.trip_id = ""
    st.session_state.trip_started_at = None
    st.session_state.trip_ended_at = None
    st.session_state.trip_total_m = 0.0
    st.session_state.cust_name = ""
    st.session_state.cust_phone = ""
    st.session_state.last_save_error = ""


# -------------------- KHÔI PHỤC PHIÊN --------------------
if not st.session_state["logged_in"] and "phone" in st.query_params:
    saved_phone = str(st.query_params["phone"])

    if saved_phone:
        _, login_records = get_worksheet_data("DANG_NHAP")

        if saved_phone.upper() == "KHÁCH HÀNG":
            st.session_state["logged_in"] = True
            st.session_state["user_phone"] = "KHÁCH HÀNG"
            st.session_state["user_name"] = "Khách hàng tự do"
        else:
            for row in login_records:
                if str(row.get("SĐT", "")).strip() == saved_phone.strip():
                    st.session_state["logged_in"] = True
                    st.session_state["user_phone"] = str(row.get("SĐT", ""))
                    st.session_state["user_name"] = str(
                        row.get("TÊN TÀI XẾ", "Thành viên")
                    )
                    break


# ============================================================
# ĐĂNG NHẬP
# ============================================================
if not st.session_state["logged_in"]:
    st.markdown("<div class='app-title'>🛵 4567 XE ÔM</div>", unsafe_allow_html=True)

    st.markdown("<div class='action-box'>", unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align:center;font-size:20px;font-weight:900;margin-bottom:8px;'>🔐 ĐĂNG NHẬP TÀI XẾ</div>",
        unsafe_allow_html=True,
    )

    phone_input = st.text_input(
        "SỐ ĐIỆN THOẠI",
        placeholder="Nhập SĐT của bác tài...",
        key="login_phone",
    )

    if st.button("🚀 ĐĂNG NHẬP", type="primary", use_container_width=True):
        if not phone_input.strip():
            st.warning("Vui lòng nhập SĐT.")
        else:
            with st.spinner("Đang kiểm tra..."):
                _, login_records = get_worksheet_data("DANG_NHAP")
                matched_user = None

                if phone_input.strip().upper() == "KHÁCH HÀNG":
                    matched_user = {
                        "SĐT": "KHÁCH HÀNG",
                        "TÊN TÀI XẾ": "Khách hàng tự do",
                        "HIỆN TRẠNG TÀI XẾ": "",
                    }
                else:
                    for row in login_records:
                        if (
                            str(row.get("SĐT", "")).strip()
                            == phone_input.strip()
                        ):
                            matched_user = row
                            break

                if matched_user:
                    st.session_state["logged_in"] = True
                    st.session_state["user_phone"] = str(
                        matched_user.get("SĐT", "")
                    )
                    st.session_state["user_name"] = str(
                        matched_user.get("TÊN TÀI XẾ", "Thành viên")
                    )

                    update_driver_status(
                        st.session_state["user_phone"], "Trực tuyến"
                    )
                    st.query_params["phone"] = st.session_state["user_phone"]
                    st.session_state["login_success_effect"] = True
                    st.rerun()
                else:
                    st.error("❌ Số điện thoại không chính xác.")

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# ============================================================
# KẾT THÚC CHUYẾN TỪ QUERY PARAMS
# GPS chạy trong trình duyệt, khi bấm KẾT THÚC sẽ gửi số mét về đây.
# ============================================================
if str(st.query_params.get("action", "")) == "stop":
    try:
        dist_val = max(0.0, float(st.query_params.get("dist", 0.0)))
    except Exception:
        dist_val = 0.0

    try:
        start_ts = float(
            st.query_params.get(
                "start", st.session_state.get("trip_started_at") or time.time()
            )
        )
    except Exception:
        start_ts = st.session_state.get("trip_started_at") or time.time()

    end_ts = time.time()

    cname = str(
        st.query_params.get(
            "cname", st.session_state.get("cust_name", "Khách vãng lai")
        )
    )
    cphone = str(
        st.query_params.get(
            "cphone", st.session_state.get("cust_phone", "")
        )
    )

    trip_id = st.session_state.get("trip_id") or f"C4567_{int(start_ts)}"

    # Nếu trình duyệt bị reload, vẫn lấy đúng thông tin từ URL.
    st.session_state.trip_active = False
    st.session_state.trip_id = trip_id
    st.session_state.trip_ended_at = end_ts
    st.session_state.trip_started_at = start_ts
    st.session_state.trip_total_m = dist_val
    st.session_state.cust_name = cname
    st.session_state.cust_phone = cphone

    time_diff = max(0, int(end_ts - start_ts))
    hh = time_diff // 3600
    mm = (time_diff % 3600) // 60
    ss = time_diff % 60
    total_time_str = f"{hh:02d}:{mm:02d}:{ss:02d}"

    km_val = round(dist_val / 1000.0, 2)
    fare_val = round(km_val * DONG_GIA)

    # 1. Ghi bản chính vào DATA_4567.
    ok, error = save_trip_to_data(
        trip_id=trip_id,
        start_ts=start_ts,
        end_ts=end_ts,
        total_time_str=total_time_str,
        cust_name=cname,
        cust_phone=cphone,
        km_val=km_val,
        fare_val=fare_val,
        driver_name=st.session_state["user_name"],
        status="HOÀN THÀNH CUỐC XE",
    )

    # 2. Chỉ xóa CACHE sau khi DATA đã ghi thành công.
    if ok:
        delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)
        st.session_state["last_save_error"] = ""
    else:
        st.session_state["last_save_error"] = (
            error or "Không thể lưu DATA_4567. CACHE_4567 được giữ nguyên để an toàn."
        )

    update_driver_status(st.session_state["user_phone"], "Trực tuyến")

    st.session_state["end_trip_effect"] = ok

    # Xóa action nhưng giữ phone để không rớt phiên.
    for p in ["action", "dist", "start", "cname", "cphone"]:
        if p in st.query_params:
            del st.query_params[p]

    st.rerun()


if st.session_state.get("login_success_effect"):
    st.toast("Đăng nhập thành công!", icon="✅")
    st.session_state["login_success_effect"] = False


# ============================================================
# HEADER APP
# ============================================================
st.markdown("<div class='app-title'>🛵 4567 XE ÔM</div>", unsafe_allow_html=True)
st.markdown(
    f"<div class='driver-line'>Tài xế: <b>{html.escape(st.session_state['user_name'])}</b> "
    f"• <span style='color:#16a34a;font-weight:900;'>● SẴN SÀNG</span></div>",
    unsafe_allow_html=True,
)

st.markdown("<div class='action-box'>", unsafe_allow_html=True)

# ============================================================
# TRẠNG THÁI 1 — CHỜ KHÁCH
# ============================================================
if not st.session_state.trip_active and not st.session_state.trip_ended_at:
    st.markdown(
        "<div class='help-line'>📍 Nhập thông tin khách → BẮT ĐẦU CHẠY → KẾT THÚC CHUYẾN</div>",
        unsafe_allow_html=True,
    )

    cust_name_in = st.text_input(
        "TÊN KHÁCH HÀNG",
        placeholder="Có thể bỏ trống",
        key="cust_name_input",
    )

    cust_phone_in = st.text_input(
        "SĐT KHÁCH HÀNG",
        placeholder="Có thể bỏ trống",
        key="cust_phone_input",
    )

    if st.button("🟢 BẮT ĐẦU CHẠY", type="primary", use_container_width=True):
        start_ts = time.time()

        st.session_state.trip_active = True
        st.session_state.trip_started_at = start_ts
        st.session_state.trip_ended_at = None
        st.session_state.trip_total_m = 0.0
        st.session_state.cust_name = (
            cust_name_in.strip() if cust_name_in.strip() else "Khách vãng lai"
        )
        st.session_state.cust_phone = cust_phone_in.strip()
        st.session_state.trip_id = f"C4567_{int(start_ts)}"

        # CACHE_4567 là điểm ghi đầu tiên khi bắt đầu chuyến.
        ok, error = save_trip_to_cache(
            trip_id=st.session_state.trip_id,
            start_ts=start_ts,
            cust_name=st.session_state.cust_name,
            cust_phone=st.session_state.cust_phone,
            driver_name=st.session_state["user_name"],
        )

        if not ok:
            st.session_state.trip_active = False
            st.session_state.last_save_error = (
                error or "Không thể ghi CACHE_4567."
            )
            st.error(
                "⚠️ Chưa thể bắt đầu vì CACHE_4567 chưa ghi được. "
                "Dữ liệu chưa bị mất."
            )
        else:
            st.session_state.last_save_error = ""
            update_driver_status(
                st.session_state["user_phone"], "Đang chạy xe"
            )
            st.rerun()


# ============================================================
# TRẠNG THÁI 2 — ĐANG CHẠY
# ============================================================
elif st.session_state.trip_active:
    current_start_ts = st.session_state.get("trip_started_at") or time.time()
    safe_cname = html.escape(
        str(st.session_state.get("cust_name", "Khách vãng lai"))
    )
    safe_cphone = html.escape(
        str(st.session_state.get("cust_phone", ""))
    )

    # components.html chỉ dùng để đọc GPS trong trình duyệt.
    # Không mở popup; mọi thao tác vẫn nằm trên cùng trang App.
    html_live_tracker = f"""
    <div class="live-card">
        <div class="live-label">CƯỚC TẠM TÍNH</div>
        <div id="price" class="live-price">0 đ</div>
        <div>
            <span id="km" class="live-km">0.00</span>
            <span class="live-rate"> km • {DONG_GIA:,.0f} đ/km</span>
        </div>

        <button id="btnStop" onclick="stopTripNow()"
            style="width:100%;margin-top:12px;background:#ef4444;color:#fff;
            border:0;border-radius:13px;padding:17px 10px;font-size:21px;
            font-weight:900;cursor:pointer;">
            🛑 KẾT THÚC CHUYẾN
        </button>

        <div id="debug_acc" class="gps-line">Đang xin quyền định vị GPS...</div>
    </div>

    <script>
    let totalMeters = 0.0;
    let lastLat = null;
    let lastLon = null;
    let watchId = null;

    const dongGia = {DONG_GIA};
    const maxAccuracy = {GPS_ACCURACY_MAX_M};
    const minMove = {MIN_MOVE_M};

    function calcCrow(lat1, lon1, lat2, lon2) {{
        const R = 6371000;
        const dLat = (lat2-lat1) * Math.PI / 180;
        const dLon = (lon2-lon1) * Math.PI / 180;
        const a =
            Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(lat1*Math.PI/180) *
            Math.cos(lat2*Math.PI/180) *
            Math.sin(dLon/2) * Math.sin(dLon/2);
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    }}

    function updateDisplay() {{
        const km = totalMeters / 1000.0;
        document.getElementById("km").innerText = km.toFixed(2);
        document.getElementById("price").innerText =
            Math.round(km * dongGia).toLocaleString("vi-VN") + " đ";
    }}

    function startGPS() {{
        if (!("geolocation" in navigator)) {{
            document.getElementById("debug_acc").innerText =
                "⚠️ Thiết bị không hỗ trợ GPS.";
            return;
        }}

        watchId = navigator.geolocation.watchPosition(
            function(pos) {{
                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;
                const acc = pos.coords.accuracy;

                document.getElementById("debug_acc").innerText =
                    "GPS: ±" + acc.toFixed(0) + " m";

                if (acc > maxAccuracy) return;

                if (lastLat === null) {{
                    lastLat = lat;
                    lastLon = lon;
                    return;
                }}

                const d = calcCrow(lastLat, lastLon, lat, lon);

                // Bỏ điểm nhảy GPS quá lớn và nhiễu nhỏ.
                if (d >= minMove && d < 150) {{
                    totalMeters += d;
                    lastLat = lat;
                    lastLon = lon;
                    updateDisplay();
                }}
            }},
            function(err) {{
                document.getElementById("debug_acc").innerText =
                    "⚠️ GPS: " + err.message;
            }},
            {{
                enableHighAccuracy: true,
                maximumAge: 0,
                timeout: 10000
            }}
        );
    }}

    function stopTripNow() {{
        const btn = document.getElementById("btnStop");
        btn.innerText = "⏳ ĐANG CHỐT ĐƠN...";
        btn.style.background = "#64748b";
        btn.disabled = true;

        if (watchId !== null) {{
            navigator.geolocation.clearWatch(watchId);
        }}

        const km = totalMeters / 1000.0;

        // Gửi kết quả về chính trang App, không mở popup/tab mới.
        let parentUrl;
        try {{
            parentUrl = new URL(window.parent.location.href);
        }} catch(e) {{
            parentUrl = new URL(window.location.href);
        }}

        parentUrl.searchParams.set("action", "stop");
        parentUrl.searchParams.set("dist", String(totalMeters));
        parentUrl.searchParams.set("start", "{current_start_ts}");
        parentUrl.searchParams.set("cname", "{safe_cname}");
        parentUrl.searchParams.set("cphone", "{safe_cphone}");
        parentUrl.searchParams.set("phone", "{html.escape(str(st.session_state.get('user_phone','')))}");

        try {{
            window.top.location.href = parentUrl.toString();
        }} catch(e) {{
            window.location.href = parentUrl.toString();
        }}
    }}

    updateDisplay();
    startGPS();
    </script>
    """

    components.html(html_live_tracker, height=190, scrolling=False)


# ============================================================
# TRẠNG THÁI 3 — ĐÃ KẾT THÚC
# ============================================================
elif not st.session_state.trip_active and st.session_state.trip_ended_at:
    if st.session_state.get("end_trip_effect"):
        st.toast("🎉 Hoàn thành chuyến xe!", icon="✅")
        st.session_state["end_trip_effect"] = False

    km = st.session_state.trip_total_m / 1000.0
    fare = round(km * DONG_GIA)

    if st.session_state.get("last_save_error"):
        st.error("⚠️ " + st.session_state["last_save_error"])
    else:
        st.markdown(
            f"""
            <div class="receipt-box">
                <div style="font-size:21px;font-weight:950;color:#0f172a;">
                    🛵 4567 XE ÔM
                </div>
                <div style="color:#64748b;font-size:13px;font-weight:800;">
                    CHUYẾN XE ĐÃ HOÀN THÀNH
                </div>
                <div style="text-align:left;font-size:15px;line-height:1.55;
                            color:#334155;margin-top:7px;">
                    <b>Khách:</b> {html.escape(str(st.session_state.get('cust_name','Khách vãng lai')))}<br>
                    <b>Quãng đường:</b> {km:.2f} km<br>
                    <b>Đơn giá:</b> {DONG_GIA:,.0f} đ/km
                </div>
                <div class="receipt-total">{fare:,.0f} VNĐ</div>
                <div style="font-size:12px;color:#64748b;">
                    Đã chuyển DATA_4567 và xử lý CACHE_4567.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("♻️ NHẬN CUỐC MỚI", type="primary", use_container_width=True):
            reset_trip()
            st.rerun()

st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# HỖ TRỢ + ĐĂNG XUẤT — GỌN Ở CUỐI TRANG
# ============================================================
c1, c2 = st.columns(2)

with c1:
    st.markdown(
        '<a href="tel:0978666620" style="display:block;text-align:center;'
        'padding:11px 5px;border-radius:11px;background:#ef4444;color:white;'
        'font-weight:900;text-decoration:none;font-size:15px;">🚨 SOS</a>',
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        '<a href="https://zalo.me/0978666620" target="_blank" '
        'style="display:block;text-align:center;padding:11px 5px;border-radius:11px;'
        'background:#0068ff;color:white;font-weight:900;text-decoration:none;'
        'font-size:15px;">💬 ZALO ADMIN</a>',
        unsafe_allow_html=True,
    )

if st.button("🔒 ĐĂNG XUẤT", use_container_width=True):
    # Nếu đang chạy mà bác tài đăng xuất, vẫn chuyển chuyến sang DATA.
    if st.session_state.trip_active:
        end_ts = time.time()
        start_ts = st.session_state.trip_started_at or end_ts
        trip_id = st.session_state.trip_id

        # Trường hợp app bị logout trước khi nhận được GPS cuối cùng:
        # dùng quãng đường hiện đang có trong session.
        km_val = round(st.session_state.trip_total_m / 1000.0, 2)
        fare_val = round(km_val * DONG_GIA)

        time_diff = max(0, int(end_ts - start_ts))
        hh = time_diff // 3600
        mm = (time_diff % 3600) // 60
        ss = time_diff % 60

        ok, error = save_trip_to_data(
            trip_id=trip_id,
            start_ts=start_ts,
            end_ts=end_ts,
            total_time_str=f"{hh:02d}:{mm:02d}:{ss:02d}",
            cust_name=st.session_state.get("cust_name", "Khách vãng lai"),
            cust_phone=st.session_state.get("cust_phone", ""),
            km_val=km_val,
            fare_val=fare_val,
            driver_name=st.session_state["user_name"],
            status="ÉP KẾT THÚC KHI ĐĂNG XUẤT",
        )

        if ok:
            delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)
        else:
            st.error(
                "⚠️ Không thể ghi DATA_4567. CACHE_4567 được giữ nguyên "
                "để tránh mất dữ liệu. Bác tài chưa nên đăng xuất lại."
            )
            st.stop()

    update_driver_status(st.session_state["user_phone"], "Ngoại tuyến")

    st.session_state.clear()
    st.query_params.clear()
    st.rerun()
