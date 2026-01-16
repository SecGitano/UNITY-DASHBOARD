import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIG & AUTH ---
BASE_URL = "https://api.unityedge.io/rest/v1/rpc"
URL_ALLOCATIONS = f"{BASE_URL}/rewards_get_allocations"
URL_BALANCE = f"{BASE_URL}/rewards_get_balance"

RAW_TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6InlHbDE2UkxxLzBzTGxac0ciLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3Z0bGxwYWd0bW5jYmt5d3NxY2NkLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI3ZWZmZWM2Zi1iYWJmLTQ0MDYtYWY0MC1hZGYxYWJlYWZlMzEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY4NjAyNjg0LCJpYXQiOjE3Njg1OTkwODQsImVtYWlsIjoiIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJ3ZWIzIiwicHJvdmlkZXJzIjpbIndlYjMiXX0sInVzZXJfbWV0YWRhdGEiOnsiY3VzdG9tX2NsYWltcyI6eyJhZGRyZXNzIjoiMHg1NmYxMTM2Y2EwMjkxZjJiYmEwZTBiOTRjY2VmNDAzMzkzZDg1Y2EyIiwiY2hhaW4iOiJldGhlcmV1bSIsImRvbWFpbiI6InVuaXR5bm9kZXMuaW8iLCJuZXR3b3JrIjoiODY5Iiwic3RhdGVtZW50IjpudWxsfSwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IndlYjM6ZXRoZXJldW06MHg1NmYxMTM2Y2EwMjkxZjJiYmEwZTBiOTRjY2VmNDAzMzkzZDg1Y2EyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoid2ViMyIsInRpbWVzdGFtcCI6MTc2NzcyNjA3NH1dLCJzZXNzaW9uX2lkIjoiZjc0MThmNTUtMzE5Ni00OWQwLTgyYjUtZGY5YWFlN2E1ZTE0IiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.wJbFwqzhRdaRsofgFhiSGO_OK_h80hCT3M3b1qV7Nsg"

HEADERS = {
    "authority": "api.unityedge.io",
    "apikey": "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c",
    "authorization": f"Bearer {RAW_TOKEN}",
    "content-type": "application/json"
}

# --- STYLING (Industrial/Dark) ---
st.set_page_config(page_title="UNITY_CORE // COMMAND", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono&display=swap');
    .stApp { background-color: #0d1117; font-family: 'JetBrains+Mono', monospace; }
    
    /* Neon Glow Metrics */
    div[data-testid="stMetric"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-bottom: 3px solid #00f2ff;
        padding: 20px; border-radius: 4px;
    }
    h1, h2, h3 { font-family: 'Orbitron', sans-serif; color: #f0f6fc; }
    .pulse { height: 10px; width: 10px; background: #00f2ff; border-radius: 50%; display: inline-block; animation: blink 2s infinite; margin-right: 8px; }
    @keyframes blink { 0% { opacity: 0.2; } 50% { opacity: 1; } 100% { opacity: 0.2; } }
    </style>
    """, unsafe_allow_html=True)

# --- DATA ENGINE ---
def fetch_balance():
    """Gets the True Total Balance"""
    try:
        # Check if the payload needs a specific arg, usually {} is fine for RPC summary
        r = requests.post(URL_BALANCE, headers=HEADERS, json={}, timeout=10)
        # Note: If this returns a list, we take the first item. If a dict, we take the value.
        res = r.json()
        if isinstance(res, list): return float(res[0].get('balance', 0)) / 1_000_000
        if isinstance(res, dict): return float(res.get('balance', 0)) / 1_000_000
        return float(res) / 1_000_000
    except: return 0.0

@st.cache_data(ttl=60)
def fetch_all_data():
    try:
        # 1. Fetch Total Balance (The $234 number)
        true_balance = fetch_balance()
        
        # 2. Fetch Allocation History
        r = requests.post(URL_ALLOCATIONS, headers=HEADERS, json={"skip": None, "take": None}, timeout=10)
        df = pd.DataFrame(r.json())
        
        # 3. Clean and Convert
        df['timestamp'] = pd.to_datetime(df['created_at'])
        df['usd_amount'] = pd.to_numeric(df['amount']) / 1_000_000
        
        return df, true_balance
    except:
        return None, 0.0

df, true_total = fetch_all_data()

# --- RENDER DASHBOARD ---

# Header
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown("<h1><span style='color:#00f2ff'>█</span> UNITY_CORE <span style='color:#8b949e;'>SYNC_v2</span></h1>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div style='text-align:right; padding-top:20px;'><span class='pulse'></span><span style='color:#00f2ff'>CORE_READY</span></div>", unsafe_allow_html=True)

if df is not None:
    # 1. TOP METRICS
    m1, m2, m3, m4 = st.columns(4)
    
    # We use the TRUE TOTAL from the balance endpoint here
    m1.metric("TRUE ACCOUNT BALANCE", f"${true_total:,.2f} USD")
    
    # Calculate difference (Referrals/Leasing/Bonuses)
    allocation_total = df['usd_amount'].sum()
    hidden_diff = true_total - allocation_total
    
    m2.metric("ALLOCATED HISTORY", f"${allocation_total:,.2f} USD")
    m3.metric("OTHER REWARDS", f"${hidden_diff:,.2f} USD", help="Bonuses, Referrals, or Uncategorized income")
    
    # Calculate 24h Change
    last_24h = df[df['timestamp'] > (datetime.now() - pd.Timedelta(hours=24))]['usd_amount'].sum()
    m4.metric("24H VELOCITY", f"+${last_24h:,.4f}", delta_color="normal")

    st.markdown("---")

    # 2. VISUALS
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.markdown("### // ACCUMULATION_TIMELINE")
        daily = df.set_index('timestamp').resample('D')['usd_amount'].sum().reset_index()
        fig = px.area(daily, x='timestamp', y='usd_amount', template="plotly_dark")
        fig.update_traces(line_color='#00f2ff', fillcolor='rgba(0, 242, 255, 0.1)')
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=20,b=0))
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown("### // BALANCE_DISTRIBUTION")
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Allocations', 'Other Rewards'],
            values=[allocation_total, hidden_diff],
            hole=.6,
            marker_colors=['#00f2ff', '#7000ff']
        )])
        fig_pie.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', showlegend=False, height=350)
        st.plotly_chart(fig_pie, use_container_width=True)

    # 3. LOGS
    st.markdown("### // TRANSACTION_RECORDS")
    st.dataframe(
        df.sort_values('timestamp', ascending=False),
        column_config={
            "timestamp": st.column_config.DatetimeColumn("DATE"),
            "usd_amount": st.column_config.NumberColumn("USD_VAL", format="$ %.6f")
        },
        use_container_width=True, hide_index=True
    )
else:
    st.error("CORE_SYNC_FAILURE: Check your Bearer token in the script.")
