import datetime
import math
import os
import time

import gspread
import pytz
import streamlit as st
import streamlit.components.v1 as components
from google.oauth2.service_account import Credentials


# ============================================================
# 4567 XE ÔM — BẢN 1000 | GỌN • 1 TRANG • CACHE → DATA
# ============================================================

st.set_page_config(
    page_title="4567 Xe Ôm",
    page_icon="🛵",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ============================================================
# 1. CẤU HÌNH
# ============================================================

SHEET_KEY = st.secrets["connections"]["gsheets"].get(
    "spreadsheet",
    "1A3-1am25vZLN57SD7pkfxxQtymCaPnCj9HgBpw5RcTY",
)

DONG_GIA = 5000
GPS_ACCURACY_MAX_M = 60
MIN_MOVE_M = 4
MAX_SINGLE_MOVE_M = 150

CACHE_SHEET = "CACHE_4567"
DATA_SHEET = "DATA_4567"
LOGIN_SHEET = "DANG_NHAP"


def get_vn_time(timestamp=None):
    vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
    if timestamp is None:
        return datetime.datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")
    return datetime.datetime.fromtimestamp(timestamp, vn_tz).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# 2. GOOGLE SHEETS
# ============================================================

@st.cache_resource
def init_google_sheet_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = dict(st.secrets["connections"]["gsheets"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)


def get_sheet():
    return init_google_sheet_client().open_by_key(SHEET_KEY)


@st.cache_data(ttl=8, show_spinner=False)
def read_records(tab_name):
    try:
        ws = get_sheet().worksheet(tab_name)
        return ws, ws.get_all_records()
    except Exception:
        return None, []


def get_ws_and_headers(tab_name):
    try:
        ws = get_sheet().worksheet(tab_name)
        headers = [str(x).strip() for x in ws.row_values(1)]
        return ws, headers
    except Exception:
        return None, []


def get_next_stt(tab_name):
    try:
        ws, records = read_records(tab_name)
        if not ws:
            return 1
        values = []
        for row in records:
            for key in ("STT", "SỐ THỨ TỰ", "STT."):
                if key in row and str(row[key]).strip():
                    try:
                        values.append(int(float(str(row[key]).strip())))
                    except Exception:
                        pass
                    break
        return max(values) + 1 if values else len(records) + 1
    except Exception:
        return 1


def normalize_header(value):
    text = str(value or "").strip().upper()
    replacements = {
        "Đ": "D",
        "Ơ": "O",
        "Ư": "U",
        "Ô": "O",
        "Ă": "A",
        "Â": "A",
        "Ê": "E",
        "É": "E",
        "È": "E",
        "Ẻ": "E",
        "Ẽ": "E",
        "Ẹ": "E",
        "Á": "A",
        "À": "A",
        "Ả": "A",
        "Ã": "A",
        "Ạ": "A",
        "Í": "I",
        "Ì": "I",
        "Ỉ": "I",
        "Ĩ": "I",
        "Ị": "I",
        "Ó": "O",
        "Ò": "O",
        "Ỏ": "O",
        "Õ": "O",
        "Ọ": "O",
        "Ú": "U",
        "Ù": "U",
        "Ủ": "U",
        "Ũ": "U",
        "Ụ": "U",
        "Ý": "Y",
        "Ỳ": "Y",
        "Ỷ": "Y",
        "Ỹ": "Y",
        "Ỵ": "Y",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return " ".join(text.split())


# Các tên tương đương để DATA_4567/CACHE_4567 luôn ghi đúng cột
FIELD_ALIASES = {
    "stt": ["STT", "SỐ THỨ TỰ"],
    "trip_id": ["MÃ CUỐC XE", "MA CUOC XE", "MÃ CHUYẾN", "MA CHUYEN"],
    "start": [
        "THỜI GIAN BẮT ĐẦU",
        "THOI GIAN BAT DAU",
        "GIỜ BẮT ĐẦU",
        "GIO BAT DAU",
        "BẮT ĐẦU",
        "BAT DAU",
    ],
    "end": [
        "THỜI GIAN KẾT THÚC",
        "THOI GIAN KET THUC",
        "GIỜ KẾT THÚC",
        "GIO KET THUC",
        "KẾT THÚC",
        "KET THUC",
    ],
    "duration": ["TỔNG THỜI GIAN", "TONG THOI GIAN", "THỜI GIAN", "THOI GIAN"],
    "cust_name": ["TÊN KHÁCH HÀNG", "TEN KHACH HANG", "KHÁCH HÀNG", "KHACH HANG"],
    "cust_phone": [
        "SĐT KHÁCH HÀNG",
        "SDT KHACH HANG",
        "SĐT KH",
        "SDT KH",
        "ĐIỆN THOẠI KHÁCH HÀNG",
        "DIEN THOAI KHACH HANG",
    ],
    "fare": [
        "TIỀN KHÁCH TRẢ",
        "TIEN KHACH TRA",
        "CƯỚC PHÍ",
        "CUOC PHI",
        "TIỀN CƯỚC",
        "TIEN CUOC",
        "DOANH THU",
    ],
    "driver": ["TÀI XẾ", "TAI XE", "TÊN TÀI XẾ", "TEN TAI XE"],
    "rate": ["ĐƠN GIÁ", "DON GIA", "ĐƠN GIÁ/KM", "DON GIA/KM"],
    "km": ["KM", "QUÃNG ĐƯỜNG", "QUANG DUONG", "QUÃNG ĐƯỜNG (KM)"],
    "revenue": ["DOANH THU", "DOANH THU CUỐC XE", "DOANH THU CHUYẾN"],
    "status": ["TRẠNG THÁI", "TRANG THAI", "TÌNH TRẠNG", "TINH TRANG"],
}


def find_header_index(headers, aliases):
    normalized = {normalize_header(h): i for i, h in enumerate(headers)}
    for alias in aliases:
        key = normalize_header(alias)
        if key in normalized:
            return normalized[key]
    return None


def build_sheet_row(tab_name, values):
    """
    values là dict theo tên logic ở FIELD_ALIASES.
    Ghi theo đúng thứ tự header đang có trên TRANG TÍNH.
    Không tự ý tạo cột mới và không phụ thuộc thứ tự cột.
    """
    ws, headers = get_ws_and_headers(tab_name)
    if not ws or not headers:
        raise RuntimeError(f"Không đọc được tiêu đề sheet {tab_name}.")

    row = [""] * len(headers)
    missing = []

    for field, value in values.items():
        idx = find_header_index(headers, FIELD_ALIASES.get(field, []))
        if idx is None:
            missing.append(field)
        else:
            row[idx] = value

    # Các trường bắt buộc để xác định đúng một cuốc xe
    required = ["stt", "trip_id", "start", "cust_name", "driver", "status"]
    missing_required = [x for x in required if x in missing]
    if missing_required:
        raise RuntimeError(
            f"{tab_name} thiếu tiêu đề cột bắt buộc: "
            + ", ".join(missing_required)
            + "."
        )

    return ws, row


def append_record(tab_name, values):
    try:
        ws, row = build_sheet_row(tab_name, values)
        ws.append_row(row, value_input_option="USER_ENTERED")
        read_records.clear()
        return True, ""
    except Exception as exc:
        return False, str(exc)


def delete_cache_trip(trip_id):
    try:
        ws, records = read_records(CACHE_SHEET)
        if not ws:
            return False

        for row_number, row in enumerate(records, start=2):
            current_id = str(row.get("MÃ CUỐC XE", "")).strip()
            if not current_id:
                # Hỗ trợ header không dấu nếu sheet đang dùng kiểu này
                current_id = str(row.get("MA CUOC XE", "")).strip()

            if current_id == str(trip_id).strip():
                ws.delete_rows(row_number)
                read_records.clear()
                return True
        return False
    except Exception:
        return False


def update_driver_status(phone, status):
    if not phone or phone == "KHÁCH HÀNG":
        return
    try:
        ws, records = read_records(LOGIN_SHEET)
        if not ws:
            return

        headers = [str(x).strip() for x in ws.row_values(1)]
        status_idx = find_header_index(
            headers,
            ["HIỆN TRẠNG TÀI XẾ", "HIEN TRANG TAI XE", "TRẠNG THÁI TÀI XẾ"],
        )
        phone_idx = find_header_index(
            headers,
            ["SĐT", "SDT", "SỐ ĐIỆN THOẠI", "SO DIEN THOAI"],
        )

        if status_idx is None or phone_idx is None:
            return

        for row_number, row in enumerate(records, start=2):
            if str(row.get(headers[phone_idx], "")).strip() == str(phone).strip():
                ws.update_cell(row_number, status_idx + 1, status)
                read_records.clear()
                return
    except Exception:
        pass


# ============================================================
# 3. GIAO DIỆN — 1 TRANG, KHÔNG POPUP, KHÔNG THANH TRẮNG THỪA
# ============================================================

st.markdown(
    """
    <style>
    /* Loại phần chrome thừa của Streamlit */
    #MainMenu {visibility: hidden;}
    header[data-testid="stHeader"] {display: none;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {display: none;}
    [data-testid="stDecoration"] {display: none;}

    .stApp {
        background: #f3f7f5;
    }

    .block-container {
        width: 100%;
        max-width: 540px;
        padding: 0.45rem 0.75rem 0.75rem 0.75rem !important;
        margin: 0 auto;
    }

    /* Không để widget/HTML chèn khoảng trắng lớn */
    div[data-testid="stVerticalBlock"] > div {
        gap: 0.35rem;
    }

    .app-title {
        text-align: center;
        color: #008f5a;
        font-size: 28px;
        line-height: 1.1;
        font-weight: 950;
        margin: 0 0 2px 0;
    }

    .driver-line {
        text-align: center;
        color: #475569;
        font-size: 14px;
        margin: 0 0 7px 0;
    }

    .card {
        background: #ffffff;
        border: 1px solid #dbe5df;
        border-radius: 16px;
        padding: 13px;
        margin: 0 0 8px 0;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.06);
    }

    .section-title {
        text-align: center;
        color: #0f172a;
        font-size: 18px;
        font-weight: 900;
        margin: 0 0 7px 0;
    }

    .hint {
        background: #ecfdf5;
        border: 1px solid #bbf7d0;
        color: #166534;
        border-radius: 11px;
        padding: 8px 10px;
        font-size: 13px;
        line-height: 1.35;
        margin-bottom: 8px;
    }

    /* Font lớn, nút rõ, ít thao tác */
    label, .stTextInput label {
        font-weight: 800 !important;
        color: #1e293b !important;
        font-size: 15px !important;
    }

    div[data-baseweb="input"] input {
        font-size: 17px !important;
        min-height: 46px !important;
    }

    div.stButton > button {
        min-height: 54px !important;
        border-radius: 12px !important;
        font-size: 19px !important;
        font-weight: 900 !important;
        padding: 7px 12px !important;
    }

    .live-label {
        color: #64748b;
        font-size: 14px;
        font-weight: 900;
        text-transform: uppercase;
        text-align: center;
        margin-top: 2px;
    }

    .live-price {
        color: #008f5a;
        font-size: 44px;
        line-height: 1;
        font-weight: 950;
        text-align: center;
        margin: 5px 0;
    }

    .live-km {
        text-align: center;
        color: #334155;
        font-size: 18px;
        font-weight: 800;
        margin-bottom: 9px;
    }

    .receipt {
        background: #ffffff;
        border: 2px dashed #94a3b8;
        border-radius: 14px;
        padding: 14px;
        margin-bottom: 8px;
    }

    .receipt-brand {
        text-align: center;
        font-size: 22px;
        font-weight: 950;
        color: #0f172a;
    }

    .receipt-sub {
        text-align: center;
        font-size: 13px;
        font-weight: 800;
        color: #64748b;
        margin-bottom: 8px;
    }

    .receipt-line {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        padding: 3px 0;
        font-size: 15px;
        color: #334155;
    }

    .receipt-total {
        text-align: center;
        color: #008f5a;
        font-size: 30px;
        font-weight: 950;
        padding-top: 6px;
    }

    .support {
        display: flex;
        gap: 7px;
        margin-top: 3px;
    }

    .support a {
        flex: 1;
        text-decoration: none;
        text-align: center;
        padding: 10px 4px;
        border-radius: 11px;
        font-size: 14px;
        font-weight: 900;
        color: #ffffff;
    }

    .sos { background: #dc2626; }
    .zalo { background: #0068ff; }

    .logout-note {
        text-align: center;
        color: #94a3b8;
        font-size: 11px;
        margin-top: 4px;
    }

    @media (max-width: 420px) {
        .block-container {
            padding-left: 8px !important;
            padding-right: 8px !important;
        }
        .app-title {font-size: 25px;}
        .live-price {font-size: 40px;}
        div.stButton > button {font-size: 18px !important;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 4. SESSION STATE
# ============================================================

DEFAULTS = {
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
    "sheet_error": "",
}

for key, value in DEFAULTS.items():
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


# ============================================================
# 5. KHÔI PHỤC PHIÊN ĐĂNG NHẬP
# ============================================================

if not st.session_state.logged_in and "phone" in st.query_params:
    saved_phone = str(st.query_params.get("phone", "")).strip()

    if saved_phone:
        _, login_records = read_records(LOGIN_SHEET)

        if saved_phone.upper() == "KHÁCH HÀNG":
            st.session_state.logged_in = True
            st.session_state.user_phone = "KHÁCH HÀNG"
            st.session_state.user_name = "Khách hàng tự do"
        else:
            for row in login_records:
                if str(row.get("SĐT", "")).strip() == saved_phone:
                    st.session_state.logged_in = True
                    st.session_state.user_phone = str(row.get("SĐT", "")).strip()
                    st.session_state.user_name = str(
                        row.get("TÊN TÀI XẾ", "Thành viên")
                    ).strip() or "Thành viên"
                    break


# ============================================================
# 6. ĐĂNG NHẬP — VẪN Ở CÙNG 1 TRANG
# ============================================================

if not st.session_state.logged_in:
    st.markdown("<div class='app-title'>🛵 4567 XE ÔM</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-title'>🔐 ĐĂNG NHẬP TÀI XẾ</div>",
        unsafe_allow_html=True,
    )

    phone_input = st.text_input(
        "SỐ ĐIỆN THOẠI",
        placeholder="Nhập SĐT của bác tài",
        key="login_phone",
    )

    if st.button("🚀 ĐĂNG NHẬP", type="primary", use_container_width=True):
        phone = phone_input.strip()

        if not phone:
            st.warning("Vui lòng nhập SĐT.")
        else:
            with st.spinner("Đang kiểm tra..."):
                _, login_records = read_records(LOGIN_SHEET)
                matched_user = None

                if phone.upper() == "KHÁCH HÀNG":
                    matched_user = {
                        "SĐT": "KHÁCH HÀNG",
                        "TÊN TÀI XẾ": "Khách hàng tự do",
                        "HIỆN TRẠNG TÀI XẾ": "",
                    }
                else:
                    for row in login_records:
                        if str(row.get("SĐT", "")).strip() == phone:
                            matched_user = row
                            break

            if matched_user:
                st.session_state.logged_in = True
                st.session_state.user_phone = str(matched_user.get("SĐT", "")).strip()
                st.session_state.user_name = (
                    str(matched_user.get("TÊN TÀI XẾ", "Thành viên")).strip()
                    or "Thành viên"
                )

                update_driver_status(st.session_state.user_phone, "Trực tuyến")
                st.query_params["phone"] = st.session_state.user_phone
                st.session_state.login_success_effect = True
                st.rerun()
            else:
                st.error("❌ Số điện thoại không chính xác.")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="support">
            <a class="sos" href="tel:0978666620">🚨 SOS</a>
            <a class="zalo" href="https://zalo.me/0978666620" target="_blank">💬 ZALO ADMIN</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


# ============================================================
# 7. XỬ LÝ KẾT THÚC CHUYẾN
#    Chỉ nhận DIST + TRIP_ID từ trình duyệt.
#    Thông tin khách vẫn lấy từ SESSION STATE, không nhét vào URL.
# ============================================================

if (
    str(st.query_params.get("action", "")).lower() == "stop"
    and st.session_state.trip_active
):
    try:
        dist_val = max(0.0, float(st.query_params.get("dist", 0.0)))
    except Exception:
        dist_val = 0.0

    incoming_trip_id = str(st.query_params.get("trip_id", "")).strip()
    current_trip_id = str(st.session_state.get("trip_id", "")).strip()

    # Chỉ xử lý nếu đúng cuốc đang chạy.
    if incoming_trip_id and incoming_trip_id != current_trip_id:
        st.error("Không khớp mã cuốc xe. Dữ liệu CACHE vẫn được giữ nguyên.")
    else:
        end_ts = time.time()
        start_ts = float(st.session_state.trip_started_at or end_ts)

        km_val = round(dist_val / 1000.0, 2)
        fare_val = round(km_val * DONG_GIA)
        duration_seconds = max(0, int(end_ts - start_ts))
        hh = duration_seconds // 3600
        mm = (duration_seconds % 3600) // 60
        ss = duration_seconds % 60
        duration_str = f"{hh:02d}:{mm:02d}:{ss:02d}"

        data_values = {
            "stt": get_next_stt(DATA_SHEET),
            "trip_id": current_trip_id,
            "start": get_vn_time(start_ts),
            "end": get_vn_time(end_ts),
            "duration": duration_str,
            "cust_name": st.session_state.get("cust_name", "Khách vãng lai"),
            "cust_phone": st.session_state.get("cust_phone", ""),
            "fare": fare_val,
            "driver": st.session_state.get("user_name", ""),
            "rate": DONG_GIA,
            "km": km_val,
            "revenue": fare_val,
            "status": "HOÀN THÀNH CUỐC XE",
        }

        ok, error = append_record(DATA_SHEET, data_values)

        if ok:
            # QUAN TRỌNG:
            # DATA ghi thành công rồi mới xóa CACHE.
            delete_cache_trip(current_trip_id)

            st.session_state.trip_active = False
            st.session_state.trip_ended_at = end_ts
            st.session_state.trip_total_m = dist_val
            st.session_state.end_trip_effect = True

            update_driver_status(st.session_state.user_phone, "Trực tuyến")

            for param in ["action", "dist", "start", "trip_id"]:
                if param in st.query_params:
                    del st.query_params[param]

            st.rerun()
        else:
            st.session_state.sheet_error = error
            st.error(
                "⚠️ Chưa thể chốt cuốc. CACHE_4567 vẫn được giữ lại để không mất dữ liệu."
            )
            st.caption(error)


if st.session_state.get("login_success_effect"):
    st.toast("Đăng nhập thành công!", icon="✅")
    st.session_state.login_success_effect = False


# ============================================================
# 8. HEADER CHÍNH
# ============================================================

st.markdown("<div class='app-title'>🛵 4567 XE ÔM</div>", unsafe_allow_html=True)
st.markdown(
    f"""
    <div class='driver-line'>
        Tài xế: <b>{st.session_state.user_name}</b>
        &nbsp;•&nbsp; <span style="color:#008f5a;font-weight:900;">● Sẵn sàng</span>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 9. TRẠNG THÁI 1 — CHỜ KHÁCH
# ============================================================

if not st.session_state.trip_active and not st.session_state.trip_ended_at:
    st.markdown("<div class='card'>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class='hint'>
            <b>HƯỚNG DẪN:</b> Nhập tên/SĐT khách nếu có → bấm
            <b>BẮT ĐẦU CHẠY</b>. Khi bắt đầu, dữ liệu được lưu vào
            <b>CACHE_4567</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='section-title'>📍 THÔNG TIN KHÁCH</div>",
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
        trip_id = f"C4567_{int(start_ts)}"

        st.session_state.trip_active = True
        st.session_state.trip_started_at = start_ts
        st.session_state.trip_id = trip_id
        st.session_state.trip_ended_at = None
        st.session_state.trip_total_m = 0.0
        st.session_state.cust_name = cust_name_in.strip() or "Khách vãng lai"
        st.session_state.cust_phone = cust_phone_in.strip()

        cache_values = {
            "stt": get_next_stt(CACHE_SHEET),
            "trip_id": trip_id,
            "start": get_vn_time(start_ts),
            "end": "---",
            "duration": "---",
            "cust_name": st.session_state.cust_name,
            "cust_phone": st.session_state.cust_phone,
            "fare": 0,
            "driver": st.session_state.user_name,
            "rate": DONG_GIA,
            "km": 0,
            "revenue": 0,
            "status": "BẮT ĐẦU CUỐC",
        }

        ok, error = append_record(CACHE_SHEET, cache_values)

        if ok:
            update_driver_status(st.session_state.user_phone, "Đang chạy xe")
            st.rerun()
        else:
            # Không cho app chạy cuốc nếu CACHE không ghi được.
            reset_trip()
            st.error("⚠️ Không thể tạo CACHE_4567. Cuốc chưa được bắt đầu.")
            st.caption(error)

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# 10. TRẠNG THÁI 2 — ĐANG CHẠY
# ============================================================

elif st.session_state.trip_active:
    current_start_ts = float(st.session_state.get("trip_started_at") or time.time())
    current_trip_id = st.session_state.get("trip_id", "")

    html_live_tracker = f"""
    <div style="font-family:Arial,sans-serif;">
        <div class="live-label">CƯỚC PHÍ TẠM TÍNH</div>
        <div id="price" class="live-price">0 đ</div>
        <div id="km" class="live-km">0.00 km &nbsp;•&nbsp; {DONG_GIA:,.0f} đ/km</div>

        <button id="btnStop"
            onclick="stopTripNow()"
            style="
                width:100%;
                background:#dc2626;
                color:#fff;
                border:0;
                border-radius:12px;
                padding:16px 10px;
                font-size:21px;
                font-weight:900;
                cursor:pointer;
                box-shadow:0 4px 10px rgba(220,38,38,.25);
            ">
            🛑 KẾT THÚC CHUYẾN
        </button>

        <div id="debug_acc"
            style="text-align:center;font-size:12px;color:#64748b;margin-top:7px;">
            Đang định vị GPS...
        </div>
    </div>

    <script>
    let totalMeters = 0.0;
    let lastLat = null;
    let lastLon = null;
    let stopped = false;

    const dongGia = {DONG_GIA};
    const tripId = {current_trip_id!r};

    function calcCrow(lat1, lon1, lat2, lon2) {{
        const R = 6371000;
        const dLat = (lat2-lat1) * Math.PI/180;
        const dLon = (lon2-lon1) * Math.PI/180;
        const a =
            Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(lat1*Math.PI/180) *
            Math.cos(lat2*Math.PI/180) *
            Math.sin(dLon/2) * Math.sin(dLon/2);
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    }}

    function updateDisplay() {{
        const km = totalMeters / 1000.0;
        document.getElementById("km").innerText =
            km.toFixed(2) + " km  •  " +
            dongGia.toLocaleString("vi-VN") + " đ/km";
        document.getElementById("price").innerText =
            Math.round(km * dongGia).toLocaleString("vi-VN") + " đ";
    }}

    function stopTripNow() {{
        if (stopped) return;
        stopped = true;

        const btn = document.getElementById("btnStop");
        btn.innerText = "⏳ ĐANG CHỐT CUỐC...";
        btn.style.background = "#64748b";
        btn.disabled = true;

        const finalDist = String(Math.max(0, totalMeters));

        let parentUrl;
        try {{
            parentUrl = new URL(window.top.location.href);
        }} catch(e) {{
            parentUrl = new URL(window.location.href);
        }}

        parentUrl.searchParams.set("action", "stop");
        parentUrl.searchParams.set("dist", finalDist);
        parentUrl.searchParams.set("trip_id", tripId);

        try {{
            window.top.location.href = parentUrl.toString();
        }} catch(e) {{
            window.location.href = parentUrl.toString();
        }}
    }}

    updateDisplay();

    if ("geolocation" in navigator) {{
        navigator.geolocation.watchPosition(
            function(pos) {{
                if (stopped) return;

                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;
                const acc = pos.coords.accuracy;

                document.getElementById("debug_acc").innerText =
                    "GPS: ±" + acc.toFixed(1) + " m";

                if (acc > {GPS_ACCURACY_MAX_M}) return;

                if (lastLat === null) {{
                    lastLat = lat;
                    lastLon = lon;
                    return;
                }}

                const d = calcCrow(lastLat, lastLon, lat, lon);

                if (d >= {MIN_MOVE_M} && d < {MAX_SINGLE_MOVE_M}) {{
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
    }} else {{
        document.getElementById("debug_acc").innerText =
            "⚠️ Thiết bị không hỗ trợ GPS";
    }}
    </script>
    """

    components.html(html_live_tracker, height=220)


# ============================================================
# 11. TRẠNG THÁI 3 — BILL SAU KHI KẾT THÚC
# ============================================================

elif not st.session_state.trip_active and st.session_state.trip_ended_at:
    if st.session_state.get("end_trip_effect"):
        st.toast("🎉 Hoàn thành chuyến xe!", icon="🏆")
        st.session_state.end_trip_effect = False

    km = st.session_state.trip_total_m / 1000.0
    fare = round(km * DONG_GIA)

    st.markdown(
        f"""
        <div class='receipt'>
            <div class='receipt-brand'>🛵 4567 XE ÔM</div>
            <div class='receipt-sub'>HOÀN THÀNH CHUYẾN XE</div>

            <div class='receipt-line'>
                <span>Khách hàng</span>
                <b>{st.session_state.get("cust_name", "Khách vãng lai")}</b>
            </div>
            <div class='receipt-line'>
                <span>Quãng đường</span>
                <b>{km:.2f} km</b>
            </div>
            <div class='receipt-line'>
                <span>Đơn giá</span>
                <b>{DONG_GIA:,.0f} đ/km</b>
            </div>

            <hr style="border:0;border-top:1px dashed #94a3b8;margin:7px 0;">

            <div class='receipt-total'>{fare:,.0f} VNĐ</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("♻️ NHẬN CUỐC XE MỚI", type="primary", use_container_width=True):
        reset_trip()
        st.rerun()


# ============================================================
# 12. HỖ TRỢ + ĐĂNG XUẤT — GỌN Ở CUỐI TRANG
# ============================================================

st.markdown(
    """
    <div class="support">
        <a class="sos" href="tel:0978666620">🚨 GỌI SOS</a>
        <a class="zalo" href="https://zalo.me/0978666620" target="_blank">💬 ZALO ADMIN</a>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.button("🔒 ĐĂNG XUẤT", use_container_width=True):
    # Nếu đang chạy mà đăng xuất, bắt buộc hoàn tất dữ liệu từ CACHE → DATA.
    if st.session_state.trip_active:
        end_ts = time.time()
        start_ts = float(st.session_state.trip_started_at or end_ts)
        trip_id = st.session_state.trip_id
        km_val = round(float(st.session_state.trip_total_m) / 1000.0, 2)
        fare_val = round(km_val * DONG_GIA)

        forced_values = {
            "stt": get_next_stt(DATA_SHEET),
            "trip_id": trip_id,
            "start": get_vn_time(start_ts),
            "end": get_vn_time(end_ts),
            "duration": "00:00:00",
            "cust_name": st.session_state.get("cust_name", "Khách vãng lai"),
            "cust_phone": st.session_state.get("cust_phone", ""),
            "fare": fare_val,
            "driver": st.session_state.get("user_name", ""),
            "rate": DONG_GIA,
            "km": km_val,
            "revenue": fare_val,
            "status": "ÉP KẾT THÚC KHI ĐĂNG XUẤT",
        }

        ok, error = append_record(DATA_SHEET, forced_values)

        if not ok:
            st.error("⚠️ Không thể chuyển cuốc đang chạy sang DATA_4567.")
            st.caption(error)
            st.stop()

        delete_cache_trip(trip_id)

    update_driver_status(st.session_state.user_phone, "Ngoại tuyến")

    st.session_state.clear()
    st.query_params.clear()
    st.rerun()
