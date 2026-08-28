import math, time
import streamlit as st
from streamlit_js_eval import get_geolocation

st.set_page_config(page_title="Xeom4560 GPS TEST", page_icon="📡", layout="centered")

DONG_GIA = 5000
POLL_SECONDS = 2

for k, v in {
    "active": False, "total_m": 0.0, "count": 0,
    "last_lat": None, "last_lon": None, "last_ts": None,
    "accuracy": None, "last_delta": 0.0, "status": "Chưa bắt đầu",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def distance_m(a,b,c,d):
    R=6371000
    p1,p2=math.radians(a),math.radians(c)
    dp=math.radians(c-a); dl=math.radians(d-b)
    x=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.atan2(math.sqrt(x), math.sqrt(max(0,1-x)))

def reset():
    st.session_state.active=False
    st.session_state.total_m=0.0
    st.session_state.count=0
    st.session_state.last_lat=None
    st.session_state.last_lon=None
    st.session_state.last_ts=None
    st.session_state.accuracy=None
    st.session_state.last_delta=0.0
    st.session_state.status="Đã reset"

def process(loc):
    if not st.session_state.active: return
    if not isinstance(loc,dict):
        st.session_state.status="Không nhận được response GPS"; return
    if "error" in loc:
        e=loc.get("error") or {}
        st.session_state.status=f"GPS ERROR {e.get('code','?')}: {e.get('message','')}"
        return
    c=loc.get("coords") or {}
    lat,lon=c.get("latitude"),c.get("longitude")
    if lat is None or lon is None:
        st.session_state.status="Response có nhưng thiếu tọa độ"; return
    lat=float(lat); lon=float(lon)
    acc=c.get("accuracy")
    st.session_state.accuracy=float(acc) if acc is not None else None
    ts=float(loc.get("timestamp",time.time()*1000))/1000
    st.session_state.count += 1

    if st.session_state.last_lat is None:
        st.session_state.last_lat,st.session_state.last_lon,st.session_state.last_ts=lat,lon,ts
        st.session_state.last_delta=0
        st.session_state.status="ĐÃ NHẬN GPS — lấy mốc đầu tiên"
        return

    d=distance_m(st.session_state.last_lat,st.session_state.last_lon,lat,lon)
    dt=max(0.5,ts-st.session_state.last_ts)
    speed=d/dt*3.6
    # Diagnostic: update reference every sample; don't hide small movement.
    st.session_state.last_lat,st.session_state.last_lon,st.session_state.last_ts=lat,lon,ts
    st.session_state.last_delta=d
    if d < 0.5:
        st.session_state.status=f"GPS OK • +{d:.2f} m (chuyển động rất nhỏ)"
        return
    if speed > 250:
        st.session_state.status=f"GPS jump • {d:.1f} m / {speed:.0f} km/h — không cộng"
        return
    st.session_state.total_m += d
    st.session_state.status=f"GPS OK • +{d:.2f} m • {speed:.1f} km/h"

st.title("📡 Xeom4560 — GPS TEST")
st.caption("Bản chẩn đoán độc lập — KHÔNG dùng cho tính tiền khách thật.")

@st.fragment(run_every=POLL_SECONDS)
def tracker():
    try:
        loc=get_geolocation()
    except Exception as e:
        loc={"error":{"code":"EXCEPTION","message":str(e)}}
    if st.session_state.active:
        process(loc)

    st.subheader("📍 GPS trực tiếp")
    c=loc.get("coords") if isinstance(loc,dict) else None
    if c:
        a,b=st.columns(2)
        a.metric("Latitude",f"{float(c['latitude']):.7f}")
        b.metric("Longitude",f"{float(c['longitude']):.7f}")
        a,b=st.columns(2)
        b.metric("Accuracy",f"{float(c['accuracy']):.1f} m" if c.get("accuracy") is not None else "N/A")
        a.metric("Timestamp",str(loc.get("timestamp","N/A")))
    elif isinstance(loc,dict) and "error" in loc:
        e=loc["error"]
        st.error(f"GPS ERROR: {e.get('code','?')} — {e.get('message','')}")
    else:
        st.info("Chưa nhận được tọa độ GPS.")

    a,b,c=st.columns(3)
    a.metric("Số lần nhận",st.session_state.count)
    b.metric("Đoạn vừa nhận",f"{st.session_state.last_delta:.2f} m")
    c.metric("Tổng di chuyển",f"{st.session_state.total_m:.2f} m")
    st.write("**Trạng thái:**",st.session_state.status)
    km=st.session_state.total_m/1000
    st.markdown(f"### 💰 Cước TEST: **{km*DONG_GIA:,.2f} VNĐ**")

tracker()

if not st.session_state.active:
    if st.button("🟢 BẮT ĐẦU GPS TEST",use_container_width=True,type="primary"):
        st.session_state.active=True
        st.session_state.status="Đang chờ GPS..."
        st.rerun()
else:
    if st.button("🔴 DỪNG GPS TEST",use_container_width=True,type="primary"):
        st.session_state.active=False
        st.session_state.status="Đã dừng"
        st.rerun()
if st.button("♻️ RESET",use_container_width=True):
    reset(); st.rerun()

st.divider()
st.info("Test: Bấm BẮT ĐẦU → đứng yên 20–30 giây → chạy 100–200 m → gửi ảnh kết quả. Quan trọng nhất là Latitude, Longitude, Timestamp và Số lần nhận.")
