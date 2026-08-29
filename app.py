import datetime
import html
import pathlib
import re
import time
import uuid

import gspread
import pandas as pd
import pytz
import streamlit as st
import streamlit.components.v1 as components
from google.oauth2.service_account import Credentials


# ============================================================
# CẤU HÌNH APP
# ============================================================
st.set_page_config(
    page_title="4567 XE ÔM",
    page_icon="🛵",
    layout="centered",
    initial_sidebar_state="collapsed",
)

APP_DIR = pathlib.Path(__file__).resolve().parent
LOGO_PATH = APP_DIR / "Logo.png"

DONG_GIA = 5000
GPS_ACCURACY_MAX_M = 60
MIN_MOVE_M = 4
HOTLINE = "0978666620"
ZALO_URL = f"https://zalo.me/{HOTLINE}"


# ============================================================
# CẤU HÌNH MÚI GIỜ VIỆT NAM
# ============================================================
def get_vn_time(timestamp=None):
    vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
    if timestamp is None:
        return datetime.datetime.now(vn_tz).strftime("%Y-%m-%d %H:%M:%S")
    return datetime.datetime.fromtimestamp(timestamp, vn_tz).strftime("%Y-%m-%d %H:%M:%S")


def now_hm():
    return datetime.datetime.now(pytz.timezone("Asia/Ho_Chi_Minh")).strftime("%H:%M")


# ============================================================
# GOOGLE SHEETS
# ============================================================
SHEET_KEY = st.secrets["connections"]["gsheets"].get(
    "spreadsheet",
    "1A3-1am25vZLN57SD7pkfxxQtymCaPnCj9HgBpw5RcTY",
)


@st.cache_resource
def init_google_sheet_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_dict = dict(st.secrets["connections"]["gsheets"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)


def get_spreadsheet():
    client = init_google_sheet_client()
    try:
        return client.open_by_key(SHEET_KEY)
    except Exception:
        return client.open("4567_XEOM_2026")


def get_worksheet_data(tab_name):
    try:
        ws = get_spreadsheet().worksheet(tab_name)
        return ws, ws.get_all_records()
    except Exception as e:
        st.error(f"Lỗi kết nối Google Sheets ({tab_name}): {e}")
        return None, []


def get_next_stt(tab_name):
    try:
        _, records = get_worksheet_data(tab_name)
        return len(records) + 1 if records else 1
    except Exception:
        return 1


def append_row_to_sheet(tab_name, row_values):
    try:
        ws = get_spreadsheet().worksheet(tab_name)
        ws.append_row(row_values, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Lỗi ghi dữ liệu vào {tab_name}: {e}")
        return False


def delete_row_from_sheet(tab_name, col_name, target_val):
    try:
        ws, records = get_worksheet_data(tab_name)
        if ws is None or not records:
            return False

        for row_number, row in enumerate(records, start=2):
            if str(row.get(col_name, "")).strip() == str(target_val).strip():
                ws.delete_rows(row_number)
                return True
        return False
    except Exception as e:
        st.error(f"Lỗi xóa dữ liệu khỏi {tab_name}: {e}")
        return False


def find_header_index(ws, header_name):
    """Trả về số cột 1-based của header, hoặc None."""
    try:
        headers = ws.row_values(1)
        wanted = str(header_name).strip().casefold()
        for idx, value in enumerate(headers, start=1):
            if str(value).strip().casefold() == wanted:
                return idx
    except Exception:
        pass
    return None


def update_driver_status(phone, status):
    """
    Cập nhật cột HIỆN TRẠNG TÀI XẾ trong DANG_NHAP.
    Không tự ý thay đổi cấu trúc sheet nếu cột đã tồn tại.
    """
    if not phone or str(phone).strip().upper() == "KHÁCH HÀNG":
        return False

    try:
        ws, records = get_worksheet_data("DANG_NHAP")
        if ws is None:
            return False

        status_col = find_header_index(ws, "HIỆN TRẠNG TÀI XẾ")
        phone_col = find_header_index(ws, "SĐT")

        if status_col is None or phone_col is None:
            return False

        phone_clean = str(phone).strip()
        for row_number, row in enumerate(records, start=2):
            if str(row.get("SĐT", "")).strip() == phone_clean:
                ws.update_cell(row_number, status_col, status)
                return True

        return False
    except Exception:
        # Không làm app sập chỉ vì trạng thái Google Sheets bị lỗi.
        return False


def get_driver_status(row):
    return str(row.get("HIỆN TRẠNG TÀI XẾ", "")).strip()


def status_is_active(status):
    return "ĐANG HOẠT ĐỘNG" in status.upper() or "ĐANG CHẠY CUỐC" in status.upper()


def extract_session_token(status):
    match = re.search(r"PHIÊN:([A-Za-z0-9_-]+)", status or "")
    return match.group(1) if match else ""


def find_login_user(phone, login_records):
    phone_clean = str(phone).strip()
    if not phone_clean:
        return None

    if phone_clean.upper() == "KHÁCH HÀNG":
        return {
            "SĐT": "KHÁCH HÀNG",
            "TÊN TÀI XẾ": "Khách hàng tự do",
            "HIỆN TRẠNG TÀI XẾ": "",
        }

    for row in login_records:
        if str(row.get("SĐT", "")).strip() == phone_clean:
            return row

    return None


# ============================================================
# CSS — GIAO DIỆN GỌN, ƯU TIÊN THAO TÁC CHÍNH
# ============================================================
st.markdown(
    """
    <style>
    .stApp {
        background: #f4f7f9;
    }

    .block-container {
        max-width: 760px;
        padding-top: 0.8rem;
        padding-bottom: 2rem;
        padding-left: 0.9rem;
        padding-right: 0.9rem;
    }

    .topbar {
        background: linear-gradient(135deg, #079669 0%, #056b50 100%);
        color: #fff;
        border-radius: 20px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 10px 26px rgba(5, 107, 80, .18);
    }

    .brand-row {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .brand-name {
        font-size: 23px;
        line-height: 1.1;
        font-weight: 900;
        letter-spacing: -.4px;
    }

    .brand-sub {
        font-size: 12px;
        opacity: .88;
        margin-top: 4px;
    }

    .driver-pill {
        display: inline-block;
        margin-top: 10px;
        margin-right: 5px;
        padding: 5px 10px;
        border-radius: 999px;
        background: rgba(255,255,255,.17);
        color: #fff;
        font-size: 11px;
        font-weight: 800;
    }

    .card {
        background: #fff;
        border: 1px solid #e4e9ee;
        border-radius: 18px;
        padding: 18px;
        margin: 0 0 12px 0;
        box-shadow: 0 5px 18px rgba(15,23,42,.045);
    }

    .card-title {
        font-size: 15px;
        font-weight: 900;
        color: #102027;
        margin-bottom: 4px;
    }

    .card-desc {
        color: #64748b;
        font-size: 12px;
        line-height: 1.5;
    }

    .priority-card {
        border: 2px solid #079669;
        box-shadow: 0 8px 24px rgba(7,150,105,.10);
    }

    .fare-card {
        background: linear-gradient(135deg, #ecfdf5 0%, #f7fffb 100%);
        border: 2px solid #86efac;
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        margin-bottom: 12px;
    }

    .fare-label {
        color: #166534;
        font-size: 12px;
        font-weight: 800;
        text-transform: uppercase;
    }

    .fare-price {
        color: #0f172a;
        font-size: 38px;
        font-weight: 950;
        line-height: 1.15;
        margin: 5px 0;
    }

    .fare-meta {
        color: #475569;
        font-size: 12px;
    }

    .sos-row {
        display: flex;
        gap: 10px;
        margin-bottom: 12px;
    }

    .sos-btn {
        flex: 1;
        text-align: center;
        text-decoration: none !important;
        color: white !important;
        padding: 13px 8px;
        border-radius: 13px;
        font-size: 13px;
        font-weight: 900;
        box-shadow: 0 5px 14px rgba(15,23,42,.12);
    }

    .hotline {
        background: #dc2626;
    }

    .zalo {
        background: #0b78d0;
    }

    .success-box {
        background: linear-gradient(135deg,#ecfdf5,#f0fdf4);
        border: 1px solid #86efac;
        border-radius: 18px;
        padding: 20px;
        text-align: center;
        margin-bottom: 12px;
    }

    .success-title {
        color: #166534;
        font-size: 21px;
        font-weight: 950;
    }

    .success-sub {
        color: #475569;
        font-size: 13px;
        margin-top: 5px;
    }

    div.stButton > button {
        border-radius: 13px !important;
        min-height: 48px !important;
        font-weight: 900 !important;
        border: 0 !important;
    }

    div.stButton > button[kind="primary"] {
        background: #079669 !important;
        color: #fff !important;
        box-shadow: 0 6px 16px rgba(7,150,105,.18);
    }

    div[data-testid="stMetric"] {
        background: #fff;
        border: 1px solid #e5e7eb;
        padding: 10px;
        border-radius: 14px;
    }

    .small-note {
        color: #94a3b8;
        font-size: 11px;
        text-align: center;
        margin-top: 8px;
    }

    @media (max-width: 600px) {
        .block-container {
            padding-left: .65rem;
            padding-right: .65rem;
        }
        .fare-price {
            font-size: 32px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE
# ============================================================
defaults = {
    "logged_in": False,
    "user_phone": "",
    "user_name": "",
    "session_token": "",
    "cust_name": "",
    "cust_phone": "",
    "trip_active": False,
    "trip_id": "",
    "trip_started_at": None,
    "trip_ended_at": None,
    "trip_total_m": 0.0,
    "trip_status": "Chưa bắt đầu",
    "show_balloons": False,
    "login_success": False,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def set_logged_user(user, token=None):
    st.session_state["logged_in"] = True
    st.session_state["user_phone"] = str(user.get("SĐT", "")).strip()
    st.session_state["user_name"] = str(user.get("TÊN TÀI XẾ", "Thành viên")).strip() or "Thành viên"
    st.session_state["session_token"] = token or uuid.uuid4().hex[:8].upper()
    st.session_state["login_success"] = True


def clear_login_state():
    update_driver_status(
        st.session_state.get("user_phone", ""),
        "⚪ ĐÃ ĐĂNG XUẤT",
    )
    st.session_state["logged_in"] = False
    st.session_state["user_phone"] = ""
    st.session_state["user_name"] = ""
    st.session_state["session_token"] = ""
    st.session_state["trip_active"] = False
    st.query_params.clear()


def reset_trip():
    st.session_state["trip_active"] = False
    st.session_state["trip_started_at"] = None
    st.session_state["trip_ended_at"] = None
    st.session_state["trip_total_m"] = 0.0
    st.session_state["trip_status"] = "Chưa bắt đầu"
    st.session_state["show_balloons"] = False
    st.session_state["trip_id"] = ""


# ============================================================
# TỰ ĐỘNG ĐĂNG NHẬP BẰNG GHI NHỚ
# ============================================================
if not st.session_state["logged_in"] and "phone" in st.query_params:
    saved_phone = str(st.query_params.get("phone", "")).strip()
    saved_token = str(st.query_params.get("session", "")).strip()

    if saved_phone:
        _, login_records = get_worksheet_data("DANG_NHAP")
        matched_user = find_login_user(saved_phone, login_records)

        if matched_user:
            current_status = get_driver_status(matched_user)
            current_token = extract_session_token(current_status)

            # Khách hàng tự do không bị khóa phiên.
            is_customer = saved_phone.upper() == "KHÁCH HÀNG"

            # Nếu cùng trình duyệt/phiên đã được ghi nhớ -> cho vào.
            same_session = bool(saved_token and current_token and saved_token == current_token)

            # Nếu tài khoản đang hoạt động bởi một phiên khác -> chặn.
            if not is_customer and status_is_active(current_status) and not same_session:
                st.query_params.clear()
                st.markdown(
                    """
                    <div class="card priority-card">
                        <div class="card-title">🔒 TÀI KHOẢN ĐANG ĐƯỢC SỬ DỤNG</div>
                        <div class="card-desc">
                            Tài khoản này đang có một phiên đăng nhập khác.
                            Vui lòng không đăng nhập đồng thời trên hai thiết bị.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.error("Nếu bác tài đã đóng app nhưng trạng thái vẫn còn, hãy đăng nhập lại sau khi ADMIN đặt trạng thái tài xế về ĐÃ ĐĂNG XUẤT.")
                st.stop()

            set_logged_user(matched_user, saved_token or None)

            if not is_customer:
                update_driver_status(
                    st.session_state["user_phone"],
                    f"🟢 ĐANG HOẠT ĐỘNG • {now_hm()} • PHIÊN:{st.session_state['session_token']}",
                )

            st.rerun()


# ============================================================
# MÀN HÌNH ĐĂNG NHẬP
# ============================================================
if not st.session_state["logged_in"]:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=150)

    st.markdown(
        """
        <div class="topbar">
            <div class="brand-name">🛵 4567 XE ÔM</div>
            <div class="brand-sub">Ứng dụng điều hành chuyến xe dành cho bác tài</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="sos-row">
            <a class="sos-btn hotline" href="tel:{HOTLINE}">📞 GỌI HOTLINE</a>
            <a class="sos-btn zalo" href="{ZALO_URL}" target="_blank">💬 ZALO</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="card priority-card">
            <div class="card-title">🔐 ĐĂNG NHẬP BÁC TÀI</div>
            <div class="card-desc">
                Chỉ sử dụng số điện thoại đã được ADMIN cấp trong trang tính DANG_NHAP.
                Sau khi đăng nhập, tài khoản sẽ được đánh dấu đang hoạt động để tránh đăng nhập trùng.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    phone_input = st.text_input(
        "Số điện thoại tài xế / tài khoản:",
        placeholder="Ví dụ: 09xxxxxxxx hoặc KHÁCH HÀNG",
        key="login_phone_input",
    )

    remember_me = st.checkbox(
        "💾 Ghi nhớ đăng nhập (Không cần nhập lại lần sau)",
        value=True,
        key="remember_login",
    )

    if st.button("🚀 ĐĂNG NHẬP", type="primary", use_container_width=True):
        phone_clean = phone_input.strip()

        if not phone_clean:
            st.warning("Vui lòng nhập tài khoản đăng nhập.")
        else:
            with st.spinner("Đang xác thực tài khoản..."):
                _, login_records = get_worksheet_data("DANG_NHAP")
                matched_user = find_login_user(phone_clean, login_records)

                if not matched_user:
                    st.error("❌ Tài khoản không tồn tại trong danh sách phân quyền DANG_NHAP.")
                else:
                    current_status = get_driver_status(matched_user)
                    is_customer = phone_clean.upper() == "KHÁCH HÀNG"

                    if not is_customer and status_is_active(current_status):
                        st.error(
                            "🔒 Tài khoản này đang được đăng nhập/hoạt động trên một thiết bị khác. "
                            "Vui lòng không dùng cùng một ID đồng thời."
                        )
                    else:
                        set_logged_user(matched_user)

                        if not is_customer:
                            update_driver_status(
                                st.session_state["user_phone"],
                                f"🟢 ĐANG HOẠT ĐỘNG • {now_hm()} • PHIÊN:{st.session_state['session_token']}",
                            )

                        if remember_me:
                            st.query_params["phone"] = st.session_state["user_phone"]
                            st.query_params["session"] = st.session_state["session_token"]
                        else:
                            st.query_params.clear()

                        st.success(
                            f"✅ ĐĂNG NHẬP THÀNH CÔNG! Xin chào {st.session_state['user_name']}."
                        )
                        st.balloons()
                        time.sleep(1.2)
                        st.rerun()

    st.markdown(
        '<div class="small-note">4567 XE ÔM • Hệ thống trực tuyến</div>',
        unsafe_allow_html=True,
    )
    st.stop()


# ============================================================
# HÀM IN BILL
# ============================================================
def render_print_bill(km, fare, start_time, end_time, duration, customer, customer_phone, driver):
    customer = html.escape(str(customer or "Khách vãng lai"))
    customer_phone = html.escape(str(customer_phone or "---"))
    driver = html.escape(str(driver or "---"))
    trip_id = html.escape(str(st.session_state.get("trip_id", "---")))

    bill_html = f"""
    <div style="
        font-family:Arial,sans-serif;
        background:#fff;
        max-width:430px;
        margin:0 auto;
        padding:22px;
        border:1px solid #ddd;
        border-radius:16px;
        color:#111827;
    ">
        <div style="text-align:center;border-bottom:1px dashed #aaa;padding-bottom:12px;">
            <div style="font-size:24px;font-weight:900;">4567 XE ÔM</div>
            <div style="font-size:12px;color:#64748b;">PHIẾU THANH TOÁN CHUYẾN XE</div>
        </div>

        <div style="padding:14px 0;font-size:13px;line-height:1.8;">
            <b>Mã cuốc:</b> {trip_id}<br>
            <b>Khách hàng:</b> {customer}<br>
            <b>SĐT khách:</b> {customer_phone}<br>
            <b>Tài xế:</b> {driver}<br>
            <b>Bắt đầu:</b> {html.escape(start_time)}<br>
            <b>Kết thúc:</b> {html.escape(end_time)}<br>
            <b>Thời gian:</b> {html.escape(duration)}
        </div>

        <div style="border-top:1px dashed #aaa;padding-top:12px;">
            <div style="display:flex;justify-content:space-between;font-size:14px;">
                <span>Quãng đường</span><b>{km:.2f} km</b>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:14px;margin-top:6px;">
                <span>Đơn giá</span><b>{DONG_GIA:,.0f} đ/km</b>
            </div>
            <div style="
                display:flex;
                justify-content:space-between;
                margin-top:14px;
                padding-top:12px;
                border-top:1px solid #ddd;
                font-size:21px;
                font-weight:900;
            ">
                <span>TỔNG THANH TOÁN</span>
                <span>{fare:,.0f} VNĐ</span>
            </div>
        </div>

        <div style="text-align:center;margin-top:18px;color:#64748b;font-size:11px;">
            Cảm ơn quý khách đã sử dụng 4567 XE ÔM
        </div>

        <button onclick="window.print()" style="
            width:100%;
            margin-top:16px;
            padding:13px;
            border:0;
            border-radius:10px;
            background:#079669;
            color:#fff;
            font-size:14px;
            font-weight:900;
            cursor:pointer;
        ">🖨️ IN BILL</button>
    </div>

    <style>
    @media print {{
        button {{ display:none !important; }}
        body {{ margin:0; background:#fff; }}
    }}
    </style>
    """
    components.html(bill_html, height=610)


# ============================================================
# GIAO DIỆN CHÍNH — HEADER
# ============================================================
col_logo, col_info = st.columns([1, 4], vertical_alignment="center")

with col_logo:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=100)
    else:
        st.markdown(
            '<div style="font-size:42px;text-align:center;">🛵</div>',
            unsafe_allow_html=True,
        )

with col_info:
    driver_name = html.escape(st.session_state["user_name"])
    driver_phone = html.escape(st.session_state["user_phone"])

    st.markdown(
        f"""
        <div class="topbar" style="margin:0;">
            <div class="brand-name">4567 XE ÔM</div>
            <div class="brand-sub">Xin chào, {driver_name}</div>
            <span class="driver-pill">👤 {driver_phone}</span>
            <span class="driver-pill">🟢 ĐANG TRỰC</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SOS — ĐẶT NGAY DƯỚI HEADER, LUÔN DỄ BẤM
# ============================================================
st.markdown(
    f"""
    <div class="sos-row">
        <a class="sos-btn hotline" href="tel:{HOTLINE}">📞 HOTLINE {HOTLINE}</a>
        <a class="sos-btn zalo" href="{ZALO_URL}" target="_blank">💬 ZALO HỖ TRỢ</a>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HIỆU ỨNG ĐĂNG NHẬP THÀNH CÔNG
# ============================================================
if st.session_state.get("login_success", False):
    st.markdown(
        f"""
        <div class="success-box">
            <div class="success-title">🎉 ĐĂNG NHẬP THÀNH CÔNG!</div>
            <div class="success-sub">
                Xin chào <b>{html.escape(st.session_state["user_name"])}</b>.
                Chúc bác tài một ngày chạy xe thuận lợi! 🛵
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.toast("✅ Đăng nhập thành công!", icon="🎉")
    st.balloons()
    st.session_state["login_success"] = False


# ============================================================
# CẬP NHẬT TRẠNG THÁI TÀI XẾ
# ============================================================
if not st.session_state["trip_active"]:
    update_driver_status(
        st.session_state["user_phone"],
        f"🟢 ĐANG HOẠT ĐỘNG • {now_hm()} • PHIÊN:{st.session_state['session_token']}",
    )
else:
    update_driver_status(
        st.session_state["user_phone"],
        f"🟢 ĐANG CHẠY CUỐC • {now_hm()} • PHIÊN:{st.session_state['session_token']}",
    )


# ============================================================
# XỬ LÝ KẾT THÚC CHUYẾN XE QUA URL PARAMS
# ============================================================
if st.query_params.get("action", "") == "stop":
    try:
        dist_val = float(st.query_params.get("dist", 0.0))
    except (TypeError, ValueError):
        dist_val = 0.0

    try:
        start_ts = float(st.query_params.get("start", time.time()))
    except (TypeError, ValueError):
        start_ts = time.time()

    cname = st.query_params.get(
        "cname",
        st.session_state.get("cust_name", "Khách vãng lai"),
    )
    cphone = st.query_params.get(
        "cphone",
        st.session_state.get("cust_phone", ""),
    )

    end_ts = time.time()
    st.session_state["cust_name"] = cname
    st.session_state["cust_phone"] = cphone
    st.session_state["trip_active"] = False
    st.session_state["trip_ended_at"] = end_ts
    st.session_state["trip_total_m"] = max(0.0, dist_val)
    st.session_state["trip_status"] = "Đã hoàn thành"

    start_time_str = get_vn_time(start_ts)
    end_time_str = get_vn_time(end_ts)

    time_diff = max(0, int(end_ts - start_ts))
    hh, mm, ss = time_diff // 3600, (time_diff % 3600) // 60, time_diff % 60
    total_time_str = f"{hh:02d}:{mm:02d}:{ss:02d}"

    km_val = round(dist_val / 1000.0, 2)
    fare_val = round(km_val * DONG_GIA)
    trip_id = f"C4567_{int(start_ts)}"
    st.session_state["trip_id"] = trip_id

    stt = get_next_stt("DATA_4567")
    row_data = [
        stt,
        trip_id,
        start_time_str,
        end_time_str,
        total_time_str,
        cname,
        cphone,
        fare_val,
        st.session_state["user_name"],
        DONG_GIA,
        km_val,
        fare_val,
        "HOÀN THÀNH CUỐC XE",
    ]

    append_row_to_sheet("DATA_4567", row_data)
    delete_row_from_sheet("CACHE_4567", "MÃ CUỐC XE", trip_id)

    update_driver_status(
        st.session_state["user_phone"],
        f"🟢 ĐANG HOẠT ĐỘNG • {now_hm()} • PHIÊN:{st.session_state['session_token']}",
    )

    st.session_state["show_balloons"] = True

    # Giữ phone + session để chế độ ghi nhớ tiếp tục hoạt động.
    phone_val = st.query_params.get("phone", st.session_state["user_phone"])
    session_val = st.query_params.get("session", st.session_state["session_token"])
    st.query_params.clear()
    if phone_val:
        st.query_params["phone"] = phone_val
    if session_val:
        st.query_params["session"] = session_val

    st.rerun()


# ============================================================
# TRẠNG THÁI 1 — SẴN SÀNG NHẬN KHÁCH
# ============================================================
if not st.session_state["trip_active"] and not st.session_state["trip_ended_at"]:
    st.markdown(
        """
        <div class="card priority-card">
            <div class="card-title">🚦 SẴN SÀNG NHẬN KHÁCH</div>
            <div class="card-desc">
                Nhập thông tin khách nếu có, sau đó bấm BẮT ĐẦU CUỐC XE.
                GPS sẽ bắt đầu tính quãng đường ngay khi chuyến xe được kích hoạt.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        cust_name_in = st.text_input(
            "Tên khách hàng",
            placeholder="VD: Anh Nam",
            key="customer_name_input",
        )
    with c2:
        cust_phone_in = st.text_input(
            "SĐT khách",
            placeholder="VD: 0912345678",
            key="customer_phone_input",
        )

    if st.button("🟢 BẮT ĐẦU CUỐC XE", type="primary", use_container_width=True):
        reset_trip()

        st.session_state["trip_active"] = True
        st.session_state["trip_started_at"] = time.time()
        st.session_state["cust_name"] = (
            cust_name_in.strip() if cust_name_in.strip() else "Khách vãng lai"
        )
        st.session_state["cust_phone"] = cust_phone_in.strip()
        st.session_state["trip_id"] = f"C4567_{int(st.session_state['trip_started_at'])}"

        start_time_str = get_vn_time(st.session_state["trip_started_at"])

        stt_cache = get_next_stt("CACHE_4567")
        cache_row = [
            stt_cache,
            st.session_state["trip_id"],
            start_time_str,
            "---",
            "---",
            st.session_state["cust_name"],
            st.session_state["cust_phone"],
            0,
            st.session_state["user_name"],
            DONG_GIA,
            0,
            0,
            "BẮT ĐẦU CUỐC",
        ]

        append_row_to_sheet("CACHE_4567", cache_row)

        update_driver_status(
            st.session_state["user_phone"],
            f"🟢 ĐANG CHẠY CUỐC • {now_hm()} • PHIÊN:{st.session_state['session_token']}",
        )

        st.rerun()


# ============================================================
# TRẠNG THÁI 2 — CHUYẾN XE ĐANG DIỄN RA
# ============================================================
elif st.session_state["trip_active"]:
    customer_display = html.escape(
        st.session_state.get("cust_name", "Khách vãng lai")
    )
    customer_phone_display = html.escape(
        st.session_state.get("cust_phone", "---") or "---"
    )

    st.markdown(
        f"""
        <div class="card priority-card">
            <div class="card-title" style="color:#079669;">🟢 CHUYẾN XE ĐANG DIỄN RA</div>
            <div class="card-desc">
                Khách: <b>{customer_display}</b>
                &nbsp;•&nbsp;
                SĐT: <b>{customer_phone_display}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    current_start_ts = st.session_state.get("trip_started_at", time.time())

    html_live_tracker = f"""
    <div style="
        font-family:system-ui,-apple-system,sans-serif;
        background:#fff;
        border:1px solid #e2e8f0;
        border-radius:20px;
        padding:18px;
        text-align:center;
        box-shadow:0 6px 18px rgba(15,23,42,.05);
    ">
        <div style="
            background:linear-gradient(135deg,#ecfdf5,#f7fffb);
            border:1px solid #86efac;
            border-radius:16px;
            padding:18px;
            margin-bottom:14px;
        ">
            <div style="color:#166534;font-size:12px;font-weight:800;text-transform:uppercase;">
                CƯỚC PHÍ TẠM TÍNH
            </div>
            <div id="price" style="color:#0f172a;font-size:38px;font-weight:950;margin:5px 0;">
                0 VNĐ
            </div>
            <div style="color:#475569;font-size:12px;">
                <span id="km">0.00</span> km • {DONG_GIA:,.0f} đ/km
            </div>
        </div>

        <button id="btnStop" onclick="stopTripNow()" style="
            width:100%;
            background:#dc2626;
            color:#fff;
            border:none;
            border-radius:13px;
            padding:16px;
            font-size:16px;
            font-weight:900;
            cursor:pointer;
            box-shadow:0 5px 14px rgba(220,38,38,.20);
        ">
            🏁 KẾT THÚC CHUYẾN XE
        </button>

        <div id="debug_acc" style="
            font-size:11px;
            color:#94a3b8;
            margin-top:10px;
        ">
            GPS: Đang theo dõi...
        </div>
    </div>

    <script>
    localStorage.setItem("xeom_trip_active", "true");
    localStorage.setItem("xeom_start_time", "{current_start_ts}");

    function calcCrow(lat1, lon1, lat2, lon2) {{
        var R = 6371000;
        var dLat = (lat2 - lat1) * Math.PI / 180;
        var dLon = (lon2 - lon1) * Math.PI / 180;
        var a =
            Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(lat1 * Math.PI / 180) *
            Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon/2) * Math.sin(dLon/2);
        return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    }}

    let lastLat = null;
    let lastLon = null;
    let totalMeters = parseFloat(
        localStorage.getItem("xeom_total_meters") || "0.0"
    );
    const dongGia = {DONG_GIA};

    function updateFare() {{
        let km = totalMeters / 1000.0;
        document.getElementById("km").innerText = km.toFixed(2);
        document.getElementById("price").innerText =
            Math.round(km * dongGia).toLocaleString('vi-VN') + " VNĐ";
    }}

    updateFare();

    if ("geolocation" in navigator) {{
        navigator.geolocation.watchPosition(
            function(pos) {{
                let lat = pos.coords.latitude;
                let lon = pos.coords.longitude;
                let acc = pos.coords.accuracy;

                document.getElementById("debug_acc").innerText =
                    "GPS: Sai số ±" + acc.toFixed(1) + " m • Đang hoạt động";

                if (acc > {GPS_ACCURACY_MAX_M}) return;

                if (lastLat === null) {{
                    lastLat = lat;
                    lastLon = lon;
                    return;
                }}

                let d = calcCrow(lastLat, lastLon, lat, lon);

                if (d >= {MIN_MOVE_M} && d < 120) {{
                    totalMeters += d;
                    lastLat = lat;
                    lastLon = lon;
                    localStorage.setItem("xeom_total_meters", totalMeters);
                    updateFare();
                }}
            }},
            function(err) {{
                document.getElementById("debug_acc").innerText =
                    "⚠️ GPS: " + err.message;
            }},
            {{
                enableHighAccuracy:true,
                maximumAge:0,
                timeout:15000
            }}
        );
    }}

    function stopTripNow() {{
        let btn = document.getElementById("btnStop");
        btn.innerText = "⏳ ĐANG CHỐT CƯỚC...";
        btn.style.background = "#64748b";
        btn.disabled = true;

        let finalDist =
            localStorage.getItem("xeom_total_meters") || "0";

        localStorage.removeItem("xeom_total_meters");
        localStorage.removeItem("xeom_trip_active");
        localStorage.removeItem("xeom_start_time");

        let baseUrl = window.location.href.split('?')[0];

        try {{
            if (window.parent && window.parent.location) {{
                baseUrl = window.parent.location.href.split('?')[0];
            }}
        }} catch(e) {{}}

        let targetUrl =
            baseUrl +
            "?action=stop" +
            "&dist=" + encodeURIComponent(finalDist) +
            "&start={current_start_ts}";

        try {{
            window.top.location.href = targetUrl;
        }} catch(e) {{
            window.location.href = targetUrl;
        }}
    }}
    </script>
    """

    components.html(html_live_tracker, height=285)


# ============================================================
# TRẠNG THÁI 3 — HOÀN TẤT + BILL
# ============================================================
elif not st.session_state["trip_active"] and st.session_state["trip_ended_at"]:
    if st.session_state.get("show_balloons", False):
        st.balloons()
        st.session_state["show_balloons"] = False

    km = st.session_state["trip_total_m"] / 1000.0
    fare = round(km * DONG_GIA)

    st.markdown(
        f"""
        <div class="success-box">
            <div class="success-title">🎉 CHÚC MỪNG! CHUYẾN XE ĐÃ HOÀN TẤT</div>
            <div class="success-sub">
                Cước xe đã được ghi nhận. Khách hàng có thể thanh toán theo bill bên dưới.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("📏 Quãng đường", f"{km:.2f} km")
    with c2:
        st.metric("💰 Đơn giá", f"{DONG_GIA:,.0f}đ")
    with c3:
        st.metric("💵 Thành tiền", f"{fare:,.0f}đ")

    start_ts = st.session_state.get("trip_started_at") or time.time()
    end_ts = st.session_state.get("trip_ended_at") or time.time()
    duration_seconds = max(0, int(end_ts - start_ts))
    hh = duration_seconds // 3600
    mm = (duration_seconds % 3600) // 60
    ss = duration_seconds % 60
    duration = f"{hh:02d}:{mm:02d}:{ss:02d}"

    render_print_bill(
        km=km,
        fare=fare,
        start_time=get_vn_time(start_ts),
        end_time=get_vn_time(end_ts),
        duration=duration,
        customer=st.session_state.get("cust_name", "Khách vãng lai"),
        customer_phone=st.session_state.get("cust_phone", ""),
        driver=st.session_state["user_name"],
    )

    st.markdown(
        '<div class="small-note">Chỉ cần kiểm tra số tiền → IN BILL → nhận thanh toán.</div>',
        unsafe_allow_html=True,
    )

    if st.button("♻️ SẴN SÀNG NHẬN CHUYẾN MỚI", type="primary", use_container_width=True):
        reset_trip()
        update_driver_status(
            st.session_state["user_phone"],
            f"🟢 ĐANG HOẠT ĐỘNG • {now_hm()} • PHIÊN:{st.session_state['session_token']}",
        )
        st.rerun()


# ============================================================
# BÁO CÁO — ĐẨY XUỐNG CUỐI, KHÔNG LÀM RỐI MÀN HÌNH
# ============================================================
st.markdown("---")

with st.expander("📊 BÁO CÁO / DỮ LIỆU HỆ THỐNG", expanded=False):
    tab_rep1, tab_rep2 = st.tabs(
        ["📦 DATA_4567", "⚡ CACHE_4567"]
    )

    with tab_rep1:
        _, data_records = get_worksheet_data("DATA_4567")
        if data_records:
            st.dataframe(
                pd.DataFrame(data_records),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Chưa có dữ liệu trong DATA_4567.")

    with tab_rep2:
        _, cache_records = get_worksheet_data("CACHE_4567")
        if cache_records:
            st.dataframe(
                pd.DataFrame(cache_records),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success("CACHE_4567 hiện đang trống.")


# ============================================================
# ĐĂNG XUẤT — CUỐI TRANG
# ============================================================
st.write("")

if st.button("🔒 ĐĂNG XUẤT TÀI KHOẢN", use_container_width=True):
    if st.session_state["trip_active"]:
        st.warning(
            "⚠️ Bác tài đang có chuyến xe. Vui lòng KẾT THÚC CHUYẾN XE trước khi đăng xuất."
        )
    else:
        clear_login_state()
        st.success("Đã đăng xuất. Hẹn gặp lại bác tài!")
        time.sleep(.7)
        st.rerun()
