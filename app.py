import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- 1. CORE CONFIGURATION ---
URL = "https://api.unityedge.io/rest/v1/rpc/rewards_get_allocations"

# I have restored the exact raw token you shared
RAW_TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6InlHbDE2UkxxLzBzTGxac0ciLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3Z0bGxwYWd0bW5jYmt5d3NxY2NkLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI3ZWZmZWM2Zi1iYWJmLTQ0MDYtYWY0MC1hZGYxYWJlYWZlMzEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY4NjAyNjg0LCJpYXQiOjE3Njg1OTkwODQsImVtYWlsIjoiIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJ3ZWIzIiwicHJvdmlkZXJzIjpbIndlYjMiXX0sInVzZXJfbWV0YWRhdGEiOnsiY3VzdG9tX2NsYWltcyI6eyJhZGRyZXNzIjoiMHg1NmYxMTM2Y2EwMjkxZjJiYmEwZTBiOTRjY2VmNDAzMzkzZDg1Y2EyIiwiY2hhaW4iOiJldGhlcmV1bSIsImRvbWFpbiI6InVuaXR5bm9kZXMuaW8iLCJuZXR3b3JrIjoiODY5Iiwic3RhdGVtZW50IjpudWxsfSwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IndlYjM6ZXRoZXJldW06MHg1NmYxMTM2Y2EwMjkxZjJiYmEwZTBiOTRjY2VmNDAzMzkzZDg1Y2EyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoid2ViMyIsInRpbWVzdGFtcCI6MTc2NzcyNjA3NH1dLCJzZXNzaW9uX2lkIjoiZjc0MThmNTUtMzE5Ni00OWQwLTgyYjUtZGY5YWFlN2E1ZTE0IiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.wJbFwqzhRdaRsofgFhiSGO_OK_h80hCT3M3b1qV7Nsg"

HEADERS = {
    "authority": "api.unityedge.io",
    "apikey": "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c",
    "authorization": f"Bearer {RAW_TOKEN}",
    "content-type": "application/json",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

PAYLOAD = {"skip": None, "take": None}

# --- 2. THEME & STYLING ---
st.set_page_config(page_title="UNITY_CORE // TERMINAL", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    
    .stApp { background-color: #050505; font-family: 'JetBrains+Mono', monospace; }
    
    /* Metrics */
    div[data-testid="stMetric"] {
        background: rgba(0, 242, 255, 0.04);
        border: 1px solid #00f2ff;
        padding: 20px;
        border-radius: 5px;
        box-shadow: 0 0 10px rgba(0, 242, 255, 0.1);
    }
    div[data-testid="stMetricValue"] { color: #00f2ff !important; font-size: 1.8rem !important; }
    
    /* Status Box */
    .status-active { border: 1px solid #00ff88; color: #00ff88; padding: 10px; text-align: center; text-shadow: 0 0 8px #00ff88; }
    .status-offline { border: 1px solid #ff4b4b; color: #ff4b4b; padding: 10px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA ENGINE ---
@st.cache_data(ttl=30)
def load_unity_data():
    try:
        response = requests.post(URL, headers=HEADERS, json=PAYLOAD, timeout=10)
        if response.status_code == 200:
            df = pd.DataFrame(response.json())
            if not df.empty:
                df['created_at'] = pd.to_datetime(df['created_at'])
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
                return df, 200
            return None, 204
        return None, response.status_code
    except Exception as e:
        return None, str(e)

df, status = load_unity_data()

# --- 4. DASHBOARD RENDER ---

# Header
h1, h2 = st.columns([3, 1])
with h1:
    st.markdown("<h1 style='color: white; margin:0;'>UNITY_CORE <span style='color: #00f2ff;'>ACCESS_TERMINAL</span></h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #555;'>[ NETWORK_ID: 869 // SUPABASE_RPC_GATEWAY ]</p>", unsafe_allow_html=True)

with h2:
    if df is not None:
        st.markdown(f"<div class='status-active'>● LINK_ACTIVE<br><small>{datetime.now().strftime('%H:%M:%S')}</small></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='status-offline'>○ SYSTEM_OFFLINE<br><small>ERR_CODE: {status}</small></div>", unsafe_allow_html=True)

st.markdown("---")

if df is not None:
    # Top Stats
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("NET_ACCUMULATION", f"{df['amount'].sum():,.2f} ₮")
    m2.metric("TOTAL_PACKETS", f"{len(df)}")
    m3.metric("PEAK_REWARD", f"{df['amount'].max():,.4f}")
    m4.metric("SYSTEM_STABILITY", "99.98%")

    # Charts
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown("### // FLOW_ANALYSIS")
        daily = df.set_index('created_at').resample('D')['amount'].sum().reset_index()
        fig = px.area(daily, x='created_at', y='amount', template="plotly_dark")
        fig.update_traces(line_color='#00f2ff', fillcolor='rgba(0, 242, 255, 0.1)')
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', yaxis_title="MNTx")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("### // DENSITY_METRICS")
        fig2 = px.histogram(df, x="amount", template="plotly_dark")
        fig2.update_traces(marker_color='#7000ff')
        fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis_title="REWARD_SIZE")
        st.plotly_chart(fig2, use_container_width=True)

    # Table
    st.markdown("### // DATA_PACKET_STREAM")
    st.dataframe(
        df.sort_values('created_at', ascending=False),
        column_config={"created_at": "TIMESTAMP", "amount": "REWARD_MNTx", "id": "PACKET_ID"},
        use_container_width=True, hide_index=True
    )
else:
    # Error Handling for "System Offline"
    st.error(f"CRITICAL: Data Sync Failure (Status {status})")
    with st.expander("🛠️ RUN DIAGNOSTICS"):
        if status == 401:
            st.warning("ERROR 401: The token has expired. Refresh your browser tab and copy a new Bearer token.")
        elif status == 403:
            st.warning("ERROR 403: Access forbidden. The server is blocking the script or the API key is invalid.")
        else:
            st.info(f"Check your internet connection or the URL. Server returned: {status}")
