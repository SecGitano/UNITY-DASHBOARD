import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- SETTINGS & AUTH ---
URL = "https://api.unityedge.io/rest/v1/rpc/rewards_get_allocations"
HEADERS = {
    "authority": "api.unityedge.io",
    "apikey": "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c",
    "authorization": "Bearer eyJhbGciOiJIUzI1NiIsImtpZCI6InlHbDE2UkxxLzBzTGxac0ciLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3Z0bGxwYWd0bW5jYmt5d3NxY2NkLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI3ZWZmZWM2Zi1iYWJmLTQ0MDYtYWY0MC1hZGYxYWJlYWZlMzEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY4NjAyNjg0LCJpYXQiOjE3Njg1OTkwODQsImVtYWlsIjoiIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJ3ZWIzIiwicHJvdmlkZXJzIjpbIndlYjMiXX0sInVzZXJfbWV0YWRhdGEiOnsiY3VzdG9tX2NsYWltcyI6eyJhZGRyZXNzIjoiMHg1NmYxMTM2Y2EwMjkxZjJiYmEwZTBiOTRjY2VmNDAzMzkzZDg1Y2EyIiwiY2hhaW4iOiJldGhlcmV1bSIsImRvbWFpbiI6InVuaXR5bm9kZXMuaW8iLCJuZXR3b3JrIjoiODY5Iiwic3RhdGVtZW50IjpudWxsfSwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IndlYjM6ZXRoZXJldW06MHg1NmYxMTM2Y2EwMjkxZjJiYmEwZTBiOTRjY2VmNDAzMzkzZDg1Y2EyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoid2ViMyIsInRpbWVzdGFtcCI6MTc2NzcyNjA3NH1dLCJzZXNzaW9uX2lkIjoiZjc0MThmNTUtMzE5Ni00OWQwLTgyYjUtZGY5YWFlN2E1ZTE0IiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.wJbFwqzhRdaRsofgFhiSGO_OK_h80hCT3M3b1qV7Nsg",
    "content-type": "application/json"
}
PAYLOAD = {"skip": None, "take": None}

# --- PAGE CONFIG ---
st.set_page_config(page_title="UNITY EDGE | COMMAND", layout="wide", initial_sidebar_state="collapsed")

# --- CUSTOM CSS FOR HIGH-TECH LOOK ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'JetBrains+Mono', monospace;
        color: #00f2ff;
    }
    .stApp {
        background-color: #0a0e14;
    }
    /* Metric Card Styling */
    div[data-testid="stMetric"] {
        background: rgba(0, 242, 255, 0.05);
        border: 1px solid #00f2ff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(0, 242, 255, 0.2);
    }
    /* Status Indicator Pulsing */
    .status-pulse {
        height: 12px; width: 12px;
        background-color: #00ff88;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 10px #00ff88;
        animation: pulse 1.5s infinite;
        margin-right: 8px;
    }
    @keyframes pulse {
        0% { transform: scale(0.9); opacity: 0.7; }
        70% { transform: scale(1.2); opacity: 1; }
        100% { transform: scale(0.9); opacity: 0.7; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- DATA PROCESSING ---
@st.cache_data(ttl=300)
def fetch_data():
    try:
        r = requests.post(URL, headers=HEADERS, json=PAYLOAD)
        if r.status_code == 200:
            df = pd.DataFrame(r.json())
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            return df
        return None
    except:
        return None

df = fetch_data()

# --- HEADER SECTION ---
col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    st.markdown(f"<h1><span style='color:#00f2ff'>//</span> UNITY EDGE <span style='color:white'>CORE_MONITOR</span></h1>", unsafe_allow_html=True)
with col_h2:
    st.markdown(f"<div style='text-align:right; padding-top:20px;'><span class='status-pulse'></span> SYSTEM_ONLINE | {datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

st.markdown("---")

if df is not None:
    # --- TOP KPI ROW ---
    m1, m2, m3, m4 = st.columns(4)
    total_rewards = df['amount'].sum()
    daily_avg = df.set_index('created_at').resample('D')['amount'].sum().mean()
    
    m1.metric("TOTAL_ALLOCATIONS", len(df))
    m2.metric("NET_REWARDS", f"{total_rewards:,.2f} MNTx")
    m3.metric("DAILY_AVG", f"{daily_avg:,.2f}")
    m4.metric("NODE_STATUS", "ACTIVE", delta="100%")

    # --- CHARTS SECTION ---
    c1, c2 = st.columns([2, 1])

    with c1:
        st.markdown("### <span style='color:#00f2ff'>//</span> REWARD_TEMPORAL_FLOW", unsafe_allow_html=True)
        # Group by date for a cleaner line chart
        daily_df = df.set_index('created_at').resample('D')['amount'].sum().reset_index()
        fig = px.area(daily_df, x='created_at', y='amount', 
                      template="plotly_dark", 
                      color_discrete_sequence=['#00f2ff'])
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis_title="", yaxis_title="MNTx",
            margin=dict(l=0, r=0, t=0, b=0),
            height=350
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("### <span style='color:#00f2ff'>//</span> ALLOCATION_DISTRIBUTION", unsafe_allow_html=True)
        # Showing distribution of reward sizes
        fig_pie = px.histogram(df, x="amount", nbins=10, 
                               template="plotly_dark", 
                               color_discrete_sequence=['#7000ff'])
        fig_pie.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=0, b=0),
            height=350
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- DATA TABLE TAB ---
    st.markdown("### <span style='color:#00f2ff'>//</span> RAW_DATA_STREAM", unsafe_allow_html=True)
    
    # Stylized dataframe
    st.dataframe(
        df.sort_values(by='created_at', ascending=False),
        column_config={
            "created_at": st.column_config.DatetimeColumn("TIMESTAMP"),
            "amount": st.column_config.NumberColumn("REWARD_VAL", format="%.4f 🪙"),
            "id": st.column_config.TextColumn("TX_ID")
        },
        use_container_width=True,
        hide_index=True
    )

    # --- FOOTER ---
    st.markdown(f"<p style='text-align:center; color:#444;'>Wallet Connected: {df.iloc[0].get('wallet_address', '0x56f...5ca2')}</p>", unsafe_allow_html=True)

else:
    st.error("CRITICAL ERROR: Unable to synchronize with Unity Edge API.")
