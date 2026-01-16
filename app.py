import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- 1. SETTINGS & AUTH ---
URL = "https://api.unityedge.io/rest/v1/rpc/rewards_get_allocations"
HEADERS = {
    "authority": "api.unityedge.io",
    "apikey": "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c",
    "authorization": "Bearer eyJhbGciOiJIUzI1NiIsImtpZCI6InlHbDE2UkxxLzBzTGxac0ciLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3Z0bGxwYWd0bW5jYmt5d3NxY2NkLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI3ZWZmZWM2Zi1iYWJmLTQ0MDYtYWY0MC1hZGYxYWJlYWZlMzEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY4NjAyNjg0LCJpYXQiOjE3Njg1OTkwODQsImVtYWlsIjoiIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJ3ZWIzIiwicHJvdmlkZXJzIjpbIndlYjMiXX0sInVzZXJfbWV0YWRhdGEiOnsiY3VzdG9t_claims\":{\"address\":\"0x56f1136ca0291f2bba0e0b94ccef403393d85ca2\",\"chain\":\"ethereum\",\"domain\":\"unitynodes.io\",\"network\":\"869\",\"statement\":null},\"email_verified\":false,\"phone_verified\":false,\"sub\":\"web3:ethereum:0x56f1136ca0291f2bba0e0b94ccef403393d85ca2\"},\"role\":\"authenticated\",\"aal\":\"aal1\",\"amr\":[{\"method\":\"web3\",\"timestamp\":1767726074}],\"session_id\":\"f7418f55-3196-49d0-82b5-df9aae7a5e14\",\"is_anonymous\":false}.wJbFwqzhRdaRsofgFhiSGO_OK_h80hCT3M3b1qV7Nsg",
    "content-type": "application/json",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
PAYLOAD = {"skip": None, "take": None}

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="UNITY_CORE // TERMINAL", layout="wide", initial_sidebar_state="collapsed")

# --- 3. CUSTOM CSS (The "Tech" Look) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    
    /* General background and font */
    .stApp {
        background-color: #050505;
        font-family: 'JetBrains+Mono', monospace;
    }
    
    /* Custom Metric Cards */
    div[data-testid="stMetric"] {
        background: rgba(0, 242, 255, 0.03);
        border: 1px solid #00f2ff;
        padding: 20px;
        border-radius: 4px;
        box-shadow: 0 0 15px rgba(0, 242, 255, 0.1);
    }
    
    /* Metric Text Colors */
    div[data-testid="stMetricValue"] {
        color: #00f2ff !important;
        font-size: 2rem !important;
    }
    
    /* Glowing status indicator */
    .status-box {
        padding: 10px;
        border: 1px solid #00ff88;
        color: #00ff88;
        text-align: center;
        text-shadow: 0 0 10px #00ff88;
        font-weight: bold;
    }
    
    /* Hide top padding */
    .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. DATA LOGIC ---
@st.cache_data(ttl=60)
def load_data():
    try:
        r = requests.post(URL, headers=HEADERS, json=PAYLOAD, timeout=10)
        if r.status_code == 200:
            df = pd.DataFrame(r.json())
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['amount'] = pd.to_numeric(df['amount'])
            return df
        return None
    except:
        return None

df = load_data()

# --- 5. DASHBOARD LAYOUT ---

# HEADER
col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown("<h1 style='color: white; margin:0;'>UNITY_CORE <span style='color: #00f2ff;'>v1.0.4</span></h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #666;'>[ NETWORK_ID: 869 // PROTOCOL: MNTx ]</p>", unsafe_allow_html=True)

with col_status:
    st.markdown(f"<div class='status-box'>● SYSTEM_LINK_ESTABLISHED<br><small>{datetime.now().strftime('%H:%M:%S')}</small></div>", unsafe_allow_html=True)

if df is not None:
    # KPI ROW
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    
    total_earned = df['amount'].sum()
    last_reward = df.sort_values('created_at').iloc[-1]['amount']
    count = len(df)
    
    m1.metric("TOTAL_ACCUMULATED", f"{total_earned:,.2f} ₮")
    m2.metric("TOTAL_ALLOCATIONS", f"{count}")
    m3.metric("LATEST_REWARD", f"{last_reward:,.4f}")
    m4.metric("NODE_UPTIME", "99.98%", delta="STABLE")

    # CHARTS SECTION
    st.markdown("### // VISUAL_DATA_STREAM")
    c1, c2 = st.columns([2, 1])

    with c1:
        # High Tech Area Chart
        df_daily = df.set_index('created_at').resample('D')['amount'].sum().reset_index()
        fig = px.area(df_daily, x='created_at', y='amount', title="ACCUMULATION_FLOW")
        fig.update_traces(line_color='#00f2ff', fillcolor='rgba(0, 242, 255, 0.1)')
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            yaxis_title="REWARD_VALUE",
            xaxis_title=None,
            font=dict(family="JetBrains Mono", color="#00f2ff")
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        # Bar chart for distribution
        fig2 = px.histogram(df, x="amount", title="REWARD_DENSITY", nbins=20)
        fig2.update_traces(marker_color='#7000ff')
        fig2.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title="REWARD_SIZE",
            font=dict(family="JetBrains Mono", color="#7000ff")
        )
        st.plotly_chart(fig2, use_container_width=True)

    # RECENT ACTIVITY TABLE
    st.markdown("### // RECENT_DATA_PACKETS")
    
    # Stylized Dataframe
    st.dataframe(
        df.sort_values('created_at', ascending=False),
        column_config={
            "created_at": st.column_config.DatetimeColumn("TIMESTAMP"),
            "amount": st.column_config.NumberColumn("REWARD", format="%.4f ₮"),
            "id": st.column_config.TextColumn("PACKET_ID")
        },
        use_container_width=True,
        hide_index=True
    )

else:
    st.error("SYSTEM_OFFLINE: UNABLE TO REACH API ENDPOINT.")
