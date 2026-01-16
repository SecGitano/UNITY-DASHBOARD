import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CORE CONFIG & NEW TOKEN ---
BASE_URL = "https://api.unityedge.io/rest/v1/rpc"
URL_ALLOCATIONS = f"{BASE_URL}/rewards_get_allocations"
URL_BALANCE = f"{BASE_URL}/rewards_get_balance"

# Update this string whenever you get "JWT Expired"
RAW_TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6InlHbDE2UkxxLzBzTGxac0ciLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3Z0bGxwYWd0bW5jYmt5d3NxY2NkLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI3ZWZmZWM2Zi1iYWJmLTQ0MDYtYWY0MC1hZGYxYWJlYWZlMzEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY4NjA2MjEzLCJpYXQiOjE3Njg2MDI2MTMsImVtYWlsIjoiIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJ3ZWIzIiwicHJvdmlkZXJzIjpbIndlYjMiXX0sInVzZXJfbWV0YWRhdGEiOnsiY3VzdG9tX2NsYWltcyI6eyJhZGRyZXNzIjoiMHg1NmYxMTM2Y2EwMjkxZjJiYmEwZTBiOTRjY2VmNDAzMzkzZDg1Y2EyIiwiY2hhaW4iOiJldGhlcmV1bSIsImRvbWFpbiI6InVuaXR5bm9kZXMuaW8iLCJuZXR3b3JrIjoiODY5Iiwic3RhdGVtZW50IjpudWxsfSwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IndlYjM6ZXRoZXJldW06MHg1NmYxMTM2Y2EwMjkxZjJiYmEwZTBiOTRjY2VmNDAzMzkzZDg1Y2EyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoid2ViMyIsInRpbWVzdGFtcCI6MTc2NzcyNjA3NH1dLCJzZXNzaW9uX2lkIjoiZjc0MThmNTUtMzE5Ni00OWQwLTgyYjUtZGY5YWFlN2E1ZTE0IiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.joTxPF5AO2dgfmerHnn7FOUT4hvCKiDDSnEJ-sWVx8Q"

HEADERS = {
    "authority": "api.unityedge.io",
    "apikey": "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c",
    "authorization": f"Bearer {RAW_TOKEN}",
    "content-type": "application/json",
    "user-agent": "Mozilla/5.0"
}

# --- 2. STYLING ---
st.set_page_config(page_title="UNITY_CORE // COMMAND", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono&display=swap');
    .stApp { background-color: #0d1117; font-family: 'JetBrains+Mono', monospace; }
    div[data-testid="stMetric"] {
        background: #161b22; border: 1px solid #30363d;
        border-left: 5px solid #00f2ff; border-radius: 4px; padding: 20px;
    }
    h1, h2, h3 { font-family: 'Orbitron', sans-serif; color: #f0f6fc; letter-spacing: 2px; }
    .status-glow { color: #00ff88; text-shadow: 0 0 10px #00ff88; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA LOGIC ---

def fetch_data():
    try:
        # Request A: History
        r_alloc = requests.post(URL_ALLOCATIONS, headers=HEADERS, json={"skip": None, "take": None}, timeout=10)
        
        # Request B: Balance
        r_bal = requests.post(URL_BALANCE, headers=HEADERS, json={}, timeout=10)
        
        if r_alloc.status_code == 200 and r_bal.status_code == 200:
            # Parse History
            df = pd.DataFrame(r_alloc.json())
            df['timestamp'] = pd.to_datetime(df['created_at'])
            df['usd_amount'] = pd.to_numeric(df['amount']) / 1_000_000
            
            # Parse True Balance
            bal_data = r_bal.json()
            # Handle list vs dict response
            if isinstance(bal_data, list):
                true_bal = float(list(bal_data[0].values())[0]) / 1_000_000
            else:
                true_bal = float(list(bal_data.values())[0]) / 1_000_000
                
            return df, true_bal, 200
        else:
            return None, 0, r_alloc.status_code
    except Exception as e:
        return None, 0, str(e)

df, true_total, status = fetch_data()

# --- 4. DASHBOARD RENDER ---

# Header
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown("<h1>█ UNITY_CORE <span style='color:#8b949e;'>OS_TERMINAL</span></h1>", unsafe_allow_html=True)
with c2:
    if df is not None:
        st.markdown(f"<div style='text-align:right;'><span class='status-glow'>● SYSTEM_SYNC_OK</span><br>{datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

if df is not None:
    # KPI Row
    m1, m2, m3, m4 = st.columns(4)
    allocation_sum = df['usd_amount'].sum()
    other_rewards = true_total - allocation_sum
    
    m1.metric("TRUE BALANCE", f"${true_total:,.2f}")
    m2.metric("NODE REWARDS", f"${allocation_sum:,.2f}")
    m3.metric("OTHER/BONUS", f"${other_rewards:,.2f}")
    
    # Calc 24h change
    last_24 = df[df['timestamp'] > (datetime.now() - pd.Timedelta(days=1))]['usd_amount'].sum()
    m4.metric("24H VELOCITY", f"+${last_24:,.4f}")

    st.markdown("---")

    # Graphics
    g1, g2 = st.columns([2, 1])
    with g1:
        st.markdown("### // ACCUMULATION_FLOW")
        daily = df.set_index('timestamp').resample('D')['usd_amount'].sum().reset_index()
        fig = px.area(daily, x='timestamp', y='usd_amount', template="plotly_dark")
        fig.update_traces(line_color='#00f2ff', fillcolor='rgba(0, 242, 255, 0.1)')
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', yaxis_title="USD ($)")
        st.plotly_chart(fig, use_container_width=True)

    with g2:
        st.markdown("### // REWARD_COMPOSITION")
        fig_pie = go.Figure(data=[go.Pie(labels=['Nodes', 'Bonus'], values=[allocation_sum, other_rewards], hole=.5)])
        fig_pie.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
        fig_pie.update_traces(marker=dict(colors=['#00f2ff', '#7000ff']))
        st.plotly_chart(fig_pie, use_container_width=True)

    # Table
    st.markdown("### // TRANSACTION_LOG")
    st.dataframe(
        df.sort_values('timestamp', ascending=False),
        column_config={"timestamp": "TIME", "usd_amount": st.column_config.NumberColumn("VALUE (USD)", format="$ %.6f")},
        use_container_width=True, hide_index=True
    )

else:
    st.error(f"📡 CORE_SYNC_FAILURE (Status: {status})")
    if "401" in str(status):
        st.warning("Your Bearer Token has expired. Please grab a fresh one from the browser.")
    st.info("Check the 'RAW_TOKEN' variable at the top of your script.")
