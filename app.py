import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIG & AUTH ---
URL = "https://api.unityedge.io/rest/v1/rpc/rewards_get_allocations"
RAW_TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6InlHbDE2UkxxLzBzTGxac0ciLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3Z0bGxwYWd0bW5jYmt5d3NxY2NkLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI3ZWZmZWM2Zi1iYWJmLTQ0MDYtYWY0MC1hZGYxYWJlYWZlMzEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY4NjAyNjg0LCJpYXQiOjE3Njg1OTkwODQsImVtYWlsIjoiIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJ3ZWIzIiwicHJvdmlkZXJzIjpbIndlYjMiXX0sInVzZXJfbWV0YWRhdGEiOnsiY3VzdG9tX2NsYWltcyI6eyJhZGRyZXNzIjoiMHg1NmYxMTM2Y2EwMjkxZjJiYmEwZTBiOTRjY2VmNDAzMzkzZDg1Y2EyIiwiY2hhaW4iOiJldGhlcmV1bSIsImRvbWFpbiI6InVuaXR5bm9kZXMuaW8iLCJuZXR3b3JrIjoiODY5Iiwic3RhdGVtZW50IjpudWxsfSwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IndlYjM6ZXRoZXJldW06MHg1NmYxMTM2Y2EwMjkxZjJiYmEwZTBiOTRjY2VmNDAzMzkzZDg1Y2EyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoid2ViMyIsInRpbWVzdGFtcCI6MTc2NzcyNjA3NH1dLCJzZXNzaW9uX2lkIjoiZjc0MThmNTUtMzE5Ni00OWQwLTgyYjUtZGY5YWFlN2E1ZTE0IiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.wJbFwqzhRdaRsofgFhiSGO_OK_h80hCT3M3b1qV7Nsg"

HEADERS = {
    "authority": "api.unityedge.io",
    "apikey": "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c",
    "authorization": f"Bearer {RAW_TOKEN}",
    "content-type": "application/json"
}

# --- STYLING ---
st.set_page_config(page_title="UNITY_CORE // INDUSTRIAL", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono&display=swap');
    
    .stApp { background-color: #0d1117; font-family: 'JetBrains+Mono', monospace; }
    
    /* Glowing Metric Cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        border: 1px solid #30363d;
        border-left: 5px solid #00f2ff;
        padding: 20px;
        border-radius: 8px;
    }
    
    /* Industrial Titles */
    h1, h2, h3 { font-family: 'Orbitron', sans-serif; letter-spacing: 2px; color: #f0f6fc; }
    
    /* Pulse Animation */
    .pulse {
        display: inline-block; width: 10px; height: 10px;
        background: #00f2ff; border-radius: 50%;
        box-shadow: 0 0 10px #00f2ff;
        animation: pulse-red 2s infinite; margin-right: 10px;
    }
    @keyframes pulse-red { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }
    </style>
    """, unsafe_allow_html=True)

# --- DATA ENGINE ---
@st.cache_data(ttl=60)
def load_and_clean_data():
    try:
        r = requests.post(URL, headers=HEADERS, json={"skip": None, "take": None}, timeout=10)
        if r.status_code != 200: return None
        
        df = pd.DataFrame(r.json())
        
        # Identify columns
        date_col = next((c for c in df.columns if 'created' in c or 'time' in c), None)
        amt_col = next((c for c in df.columns if 'amount' in c or 'reward' in c), None)
        
        if date_col and amt_col:
            df[date_col] = pd.to_datetime(df[date_col])
            # CONVERSION: Micros to USD ($1 = 1,000,000 Micros)
            df['usd_amount'] = pd.to_numeric(df[amt_col]) / 1_000_000
            df = df.rename(columns={date_col: 'timestamp'})
            return df
        return None
    except:
        return None

df = load_and_clean_data()

# --- DASHBOARD LAYOUT ---

# Top Header
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown("<h1><span style='color:#00f2ff'>█</span> UNITY_CORE <span style='color:#8b949e;'>OS_TERMINAL</span></h1>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div style='text-align:right; padding-top:20px;'><span class='pulse'></span><span style='color:#00f2ff'>NODE_V869_ONLINE</span></div>", unsafe_allow_html=True)

if df is not None:
    # 1. MAIN METRICS
    m1, m2, m3, m4 = st.columns(4)
    
    total_usd = df['usd_amount'].sum()
    avg_usd = df['usd_amount'].mean()
    latest_usd = df.sort_values('timestamp').iloc[-1]['usd_amount']
    
    m1.metric("TOTAL EARNINGS", f"${total_usd:,.2f} USD")
    m2.metric("DAILY AVERAGE", f"${df.set_index('timestamp').resample('D')['usd_amount'].sum().mean():,.4f} USD")
    m3.metric("LAST PAYOUT", f"${latest_usd:,.4f}")
    m4.metric("TOTAL RECORDS", len(df))

    st.markdown("---")

    # 2. GRAPHICS ROW
    g1, g2 = st.columns([2, 1])

    with g1:
        st.markdown("### // ACCUMULATION_VELOCITY")
        # Daily aggregate for smooth line
        daily_trend = df.set_index('timestamp').resample('D')['usd_amount'].sum().reset_index()
        
        fig = px.area(daily_trend, x='timestamp', y='usd_amount', 
                      template="plotly_dark", color_discrete_sequence=['#00f2ff'])
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False, title="TIMELINE"),
            yaxis=dict(showgrid=True, gridcolor='#30363d', title="USD ($)"),
            margin=dict(l=0, r=0, t=20, b=0),
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

    with g2:
        st.markdown("### // EARNING_GOAL")
        # Visualizing progress toward a $100 goal (change target as you wish)
        target = 100.0
        progress = (total_usd / target) * 100
        
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = total_usd,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "GOAL: $100", 'font': {'size': 14, 'family': 'Orbitron'}},
            gauge = {
                'axis': {'range': [None, target], 'tickwidth': 1, 'tickcolor': "#00f2ff"},
                'bar': {'color': "#00f2ff"},
                'bgcolor': "#161b22",
                'borderwidth': 2,
                'bordercolor': "#30363d",
                'steps': [
                    {'range': [0, target*0.5], 'color': '#0d1117'},
                    {'range': [target*0.5, target], 'color': '#0d1117'}]
            }
        ))
        fig_gauge.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white", 'family': "JetBrains Mono"}, height=400)
        st.plotly_chart(fig_gauge, use_container_width=True)

    # 3. DATA STREAM
    st.markdown("### // LIVE_LOG_STREAM")
    
    # Beautify the table
    st.dataframe(
        df.sort_values('timestamp', ascending=False),
        column_config={
            "timestamp": st.column_config.DatetimeColumn("NODE_TIME", format="D MMM, HH:mm"),
            "usd_amount": st.column_config.NumberColumn("REWARD (USD)", format="$ %.6f"),
            "id": "TRANSACTION_HASH"
        },
        use_container_width=True,
        hide_index=True
    )

else:
    st.error("CORE_ERROR: CONNECTION TO UNITY_EDGE LOST. RE-SYNC REQUIRED.")
