import urllib.parse
import requests
import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation

st.set_page_config(
    page_title="Đội Xe Ôm Tin Cẩn", page_icon="🛵", layout="centered"
)

st.title("🛵 Đội Xe Ôm Tin Cẩn (45–60)")
st.caption("Minh bạch - An toàn - Tự động định vị GPS thực tế")

st.divider()


# 1. Hàm tìm địa điểm bằng chữ (Dùng cho trường hợp khẩn cấp)
def lay_danh_sach_goi_y(dia_chi):
    if not dia_chi or len(dia_chi.strip()) < 2:
        return []
    dia_chi_sach = dia_chi.replace("-", " ").strip()
    danh_sach = []
    try:
        url = f"https://photon.komoot.io/api/?q={urllib.parse.quote(dia_chi_sach + ' Đồng Nai Việt Nam')}&limit=5"
        res = requests.get(url, headers={"User-Agent": "DoiXeOmApp/1.0"}, timeout=4).json()
        if res.get("features"):
            for item in res["features"]:
                props = item.get("properties", {})
                name = props.get("name", "")
                street = props.get("street", "")
                district = props.get("district", props.get("county", ""))
                city = props.get("city", "")
                chi_tiet = ", ".join(filter(None, [name, street, district, city]))
                if not chi_tiet: chi_tiet = dia_chi_sach
                coords = item["geometry"]["coordinates"]
                danh_sach.append({"label": chi_tiet, "lat": coords[1], "lon": coords[0]})
    except Exception:
        pass
    return danh_sach


# 2. Hàm tính km lái xe thực tế (OSRM)
def tinh_so_km_thuc_te(lat1, lon1, lat2, lon2):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        res = requests.get(url, timeout=5).json()
        if "routes" in res and len(res["routes"]) > 0:
            met = res["routes"][0]["distance"]
            return round(met / 1000.0, 2)
    except Exception:
        pass
    return None


# 3. LẤY TỌA ĐỘ GPS ĐIỂM ĐÓN
st.subheader("📍 1. Vị trí đón của bạn")
dung_gps = st.checkbox("Sử dụng Vị trí GPS hiện tại của tôi", value=True)

lat1, lon1 = None, None
diem_don_text = "Vị trí GPS hiện tại của bạn"

if dung_gps:
    loc = get_geolocation()
    if loc and "coords" in loc:
        lat1 = loc["coords"]["latitude"]
        lon1 = loc["coords"]["longitude"]
        st.success(f"🎯 Đã bắt được GPS! ({lat1:.4f}, {lon1:.4f})")
    else:
        st.info("💡 Hệ thống đang dò GPS. Vui lòng bấm 'Cho phép' trên trình duyệt...")
else:
    diem_don_input = st.text_input("Hoặc gõ Điểm đón thủ công:", placeholder="Ví dụ: Ngã tư AMATA...")
    if diem_don_input:
        ds_don = lay_danh_sach_goi_y(diem_don_input)
        if ds_don:
            lat1, lon1 = ds_don[0]["lat"], ds_don[0]["lon"]
            diem_don_text = ds_don[0]["label"]

st.divider()

# 4. BẢN ĐỒ TƯƠNG TÁC CHỌN ĐIỂM ĐẾN
st.subheader("🏁 2. Nơi bạn muốn đến")
st.write("👆 **Vuốt và CHẠM TRỰC TIẾP lên bản đồ** dưới đây để ghim điểm đến.")

# Tâm bản đồ mặc định: Lấy GPS hiện tại, nếu chưa có thì lấy tạm trung tâm Đồng Nai
map_center = [lat1, lon1] if (lat1 and lon1) else [10.9574, 106.8427]

# Khởi tạo bản đồ Folium với Tile Layer URL cố định để chống lỗi xám nền
m = folium.Map(
    location=map_center, 
    zoom_start=14, 
    tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attr="© OpenStreetMap contributors"
)

# Hiển thị Điểm Đón màu Xanh lá (nếu có)
if lat1 and lon1:
    folium.Marker(
        [lat1, lon1], popup="📍 Đang đứng ở đây", tooltip="Điểm Đón",
        icon=folium.Icon(color="green", icon="user")
    ).add_to(m)

# Vẽ bản đồ ra màn hình: Đã bật tính năng Tự động bung rộng (use_container_width)
bando_du_lieu = st_folium(
    m, 
    height=450, 
    use_container_width=True, 
    returned_objects=["last_clicked"]
)

lat2, lon2 = None, None
diem_den_chon = ""

# Nhận diện thao tác khách bấm lên bản đồ
if bando_du_lieu and bando_du_lieu.get("last_clicked"):
    lat2 = bando_du_lieu["last_clicked"]["lat"]
    lon2 = bando_du_lieu["last_clicked"]["lng"]
    diem_den_chon = "Điểm đã ghim trên bản đồ"
    st.success("📍 Bạn vừa ghim điểm đến thành công! Xem cước phí bên dưới 👇")

# Trường hợp khẩn cấp (Khách gõ chữ)
with st.expander("Gõ tìm tên đường (Dùng khi không quen xài bản đồ)"):
    tim_kiem_den = st.text_input("🔍 Nhập địa điểm:", placeholder="Ví dụ: Bệnh viện Đa Khoa Đồng Nai...")
    if tim_kiem_den:
        ds_goc = lay_danh_sach_goi_y(tim_kiem_den)
        if ds_goc:
            lua_chon_labels = [item["label"] for item in ds_goc]
            chon_diem = st.selectbox("🎯 Chọn kết quả đúng nhất:", lua_chon_labels)
            for item in ds_goc:
                if item["label"] == chon_diem:
                    lat2, lon2 = item["lat"], item["lon"]
                    diem_den_chon = item["label"]
                    break

st.divider()

# 5. TÍNH KHOẢNG CÁCH, THỜI GIAN VÀ CƯỚC PHÍ
so_km = 0.0
thoi_gian_phut = 0

if lat1 and lon1 and lat2 and lon2:
    km_goc = tinh_so_km_thuc_te(lat1, lon1, lat2, lon2)
    if km_goc:
        # Bù sai số 2.5% so với Google Maps
        so_km = round(km_goc * 1.025, 2)
        thoi_gian_phut = round((so_km / 35) * 60)

        st.success(f"📏 Quãng đường lộ trình: **{so_km} km**")
        st.info(f"⏱️ Thời gian di chuyển: **Khoảng {thoi_gian_phut} phút**")
    else:
        so_km = st.number_input("⚠️ Lỗi đo đạc, nhập km thủ công:", min_value=0.5, value=5.0, step=0.5)
        thoi_gian_phut = round((so_km / 35) * 60)

# Tính tiền
DONG_GIA = 5000
gia = so_km * DONG_GIA

st.metric(label=f"💰 Tổng cước phí dự kiến ({DONG_GIA:,}đ/km)", value=f"{gia:,.0f} VNĐ")

st.divider()

# 6. ĐẶT XE
HOTLINE = "0901234567"  # Ní nhớ thay SĐT hotline của đội vào đây

if lat1 and lon1 and lat2 and lon2 and so_km > 0:
    # Link này gửi cho bác tài bấm vào mở app Google Maps đi ngay
    maps_url = f"https://www.google.com/maps/dir/?api=1&origin={lat1},{lon1}&destination={lat2},{lon2}&travelmode=driving"

    st.markdown(f"🧭 **Lộ trình trực tuyến cho Tài Xế:** [Bấm để mở Google Maps]({maps_url})")

    noi_dung_zalo = urllib.parse.quote(
        f"Chào Đội Xe, tôi muốn đặt xe:\n- Đón: {diem_don_text}\n- Đến: {diem_den_chon}\n- Quãng đường: {so_km}km (~{thoi_gian_phut} phút)\n- Cước phí: {gia:,.0f}đ"
    )
    zalo_url = f"https://zalo.me/{HOTLINE}?text={noi_dung_zalo}"

    c1, c2 = st.columns(2)
    with c1:
        st.link_button("📞 GỌI XUẤT XE NGAY", f"tel:{HOTLINE}", use_container_width=True, type="primary")
    with c2:
        st.link_button("💬 GỬI ĐƠN QUA ZALO", zalo_url, use_container_width=True)
