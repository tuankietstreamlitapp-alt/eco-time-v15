import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Test WatchPosition Realtime", page_icon="📡", layout="centered"
)

st.markdown(
    """
    <div style="text-align: center; background: linear-gradient(135deg, #d4edda, #c3e6cb); padding: 15px; border-radius: 12px; border: 1px solid #b8daff;">
        <h2 style="color: #155724; margin-bottom: 5px; font-weight: bold;">📡 TEST GPS WATCHPOSITION REALTIME</h2>
        <p style="color: #155724; font-size: 15px; font-weight: 500; margin: 0;">Kiểm tra luồng GPS liên tục bằng JavaScript gốc</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

# Đoạn HTML kết hợp JavaScript chạy trực tiếp watchPosition trên trình duyệt điện thoại
html_code = """
<div style="font-family: sans-serif; padding: 20px; background: #ffffff; border-radius: 12px; border: 2px solid #28a745; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    <h3 style="color: #28a745; margin-top: 0;">📍 Trạng thái GPS Trực Tiếp</h3>
    <p style="font-size: 16px; margin: 8px 0;"><b>Trạng thái:</b> <span id="status" style="color: #d9534f; font-weight: bold;">Đang kết nối GPS...</span></p>
    <p style="font-size: 16px; margin: 8px 0;"><b>Latitude:</b> <span id="lat" style="font-family: monospace; font-size: 18px; color: #0275d8;">--</span></p>
    <p style="font-size: 16px; margin: 8px 0;"><b>Longitude:</b> <span id="lon" style="font-family: monospace; font-size: 18px; color: #0275d8;">--</span></p>
    <p style="font-size: 16px; margin: 8px 0;"><b>Accuracy (Độ chính xác):</b> <span id="acc">--</span> m</p>
    <hr style="border: 0; border-top: 1px solid #eee; margin: 15px 0;">
    <p style="font-size: 16px; margin: 8px 0;"><b>Đoạn vừa dịch chuyển:</b> <span id="delta" style="color: #f0ad4e; font-weight: bold;">0.00</span> m</p>
    <p style="font-size: 18px; margin: 8px 0;"><b>🔥 Tổng quãng đường:</b> <span id="total" style="color: #d9534f; font-weight: bold; font-size: 22px;">0.00</span> m</p>
    <p style="font-size: 16px; margin: 8px 0;"><b>💰 Cước tạm tính (5k/km):</b> <span id="price" style="color: #28a745; font-weight: bold; font-size: 20px;">0 VNĐ</span></p>
</div>

<script>
// Hàm tính khoảng cách Haversine chuẩn xác giữa 2 tọa độ (mét)
function calcCrow(lat1, lon1, lat2, lon2) {
    var R = 6371000; // Bán kính trái đất tính bằng mét
    var dLat = toRad(lat2 - lat1);
    var dLon = toRad(lon2 - lon1);
    var lat1_rad = toRad(lat1);
    var lat2_rad = toRad(lat2);
    var a = Math.sin(dLat/2) * Math.sin(dLat/2) +
        Math.sin(dLon/2) * Math.sin(dLon/2) * Math.cos(lat1_rad) * Math.cos(lat2_rad);
    var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

function toRad(Value) {
    return Value * Math.PI / 180;
}

let lastLat = null;
let lastLon = null;
let totalMeters = 0;
let watchId = null;

if ("geolocation" in navigator) {
    document.getElementById("status").innerText = "Đang xin quyền GPS...";
    
    watchId = navigator.geolocation.watchPosition(
        function(position) {
            let lat = position.coords.latitude;
            let lon = position.coords.longitude;
            let acc = position.coords.accuracy;

            document.getElementById("lat").innerText = lat.toFixed(7);
            document.getElementById("lon").innerText = lon.toFixed(7);
            document.getElementById("acc").innerText = acc.toFixed(1);
            document.getElementById("status").innerText = "Đang stream GPS thời gian thực ✅";
            document.getElementById("status").style.color = "#28a745";

            if (lastLat !== null && lastLon !== null) {
                let d = calcCrow(lastLat, lastLon, lat, lon);
                // Lọc nhiễu: Nếu dịch chuyển dưới 0.5m hoặc nhảy cóc quá 100m trong 1 nhịp thì bỏ qua
                if (d >= 0.5 && d < 100) {
                    totalMeters += d;
                    document.getElementById("delta").innerText = d.toFixed(2);
                    document.getElementById("total").innerText = totalMeters.toFixed(2);
                    
                    let km = totalMeters / 1000.0;
                    let price = km * 5000;
                    document.getElementById("price").innerText = price.toLocaleString('vi-VN', {maximumFractionDigits: 0}) + " VNĐ";
                    
                    lastLat = lat;
                    lastLon = lon;
                } else {
                    document.getElementById("delta").innerText = "0.00 (lọc nhiễu)";
                }
            } else {
                lastLat = lat;
                lastLon = lon;
                document.getElementById("status").innerText = "Đã khóa mốc GPS đầu tiên! Hãy di chuyển.";
            }
        },
        function(error) {
            document.getElementById("status").innerText = "Lỗi GPS: " + error.message;
            document.getElementById("status").style.color = "#d9534f";
        },
        {
            enableHighAccuracy: true,
            maximumAge: 0,
            timeout: 15000
        }
    );
} else {
    document.getElementById("status").innerText = "Trình duyệt không hỗ trợ GPS!";
}
</script>
"""

# Render đoạn HTML/JS lên app Streamlit với chiều cao vừa vặn
components.html(html_code, height=360)

st.info(
    "💡 **Cách test:** Ní mở app này trên điện thoại, bấm 'Cho phép' quyền vị trí, sau đó cầm điện thoại đi bộ hoặc chạy xe ra đường 50–100m. Nhìn xem thông số **Latitude**, **Longitude** và **Tổng quãng đường** có tự động nhảy số liên tục không nhé!"
)
