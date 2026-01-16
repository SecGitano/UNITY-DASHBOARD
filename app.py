import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone

# --- 1. SETTINGS & AUTH ---
BASE_URL = "https://api.unityedge.io/rest/v1/rpc"
URL_ALLOCATIONS = f"{BASE_URL}/rewards_get_allocations"
URL_BALANCE = f"{BASE_URL}/rewards_get_balance"
API_KEY = "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c"

st.set_page_config(page_title="UNITY_CORE // TERMINAL", layout="wide")

# --- 2. THEME ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono&display=swap');
    .stApp { background-color: #0d1117; font-family: 'JetBrains+Mono', monospace; }
    [data-testid="stMetric"] { background: #161b22; border: 1px solid #30363d; border-left: 5px solid #00f2ff; padding: 20px; }
    h1, h2, h3 { font-family: 'Orbitron', sans-serif; color: #f0f6fc; }
    </style>
    """, unsafe_allow_html=True)

st.sidebar.title("🔐 AUTHENTICATION")
user_token = st.sidebar.text_area("Paste Fresh Bearer Token:", height=100)

# --- 3. REWRITTEN DATA ENGINE ---
def fetch_and_fix_data(token):
    headers = {
        "apikey": API_KEY,
        "authorization": f"Bearer {token.strip().replace('Bearer ', '')}",
        "content-type": "application/json"
    }
    try:
        # A. Fetch Balance (The "True" Total)
        r_bal = requests.post(URL_BALANCE, headers=headers, json={}, timeout=10)
        true_bal = 0.0
        if r_bal.status_code == 200:
            raw_b = r_bal.json()
            # Handle list vs dictionary response
            b_val = list(raw_b[0].values())[0] if isinstance(raw_b, list) else list(raw_b.values())[0]
            true_bal = float(b_val) / 1_000_000
        
        # B. Fetch Allocations (The History)
        r_alloc = requests.post(URL_ALLOCATIONS, headers=headers, json={"skip": None, "take": None}, timeout=10)
        if r_alloc.status_code != 200:
            return None, 0, f"Sync Error: {r_alloc.text}"
            
        df = pd.DataFrame(r_alloc.json())
        if df.empty:
            return None, true_bal, "History is empty."

        # C. FIX TIMEZONES & COLUMNS
        # Find the date column
        date_col = next((c for c in df.columns if any(k in c.lower() for k in ['time', 'date', 'created'])), None)
        amt_col = next((c for c in df.columns if any(k in c.lower() for k in ['amount', 'reward'])), None)

        # Convert to datetime AND force timezone-naive (local-ready) to prevent comparison crashes
        df['timestamp'] = pd.to_datetime(df[date_col], utc=True).dt.tz_localize(None)
        df['usd_amount'] = pd.to_numeric(df[amt_col]) / 1_000_000
        
        return df, true_bal, None

    except Exception as e:
        return None, 0, str(e)

# --- 4. DASHBOARD RENDER ---
st.markdown("<h1>█ UNITY_CORE <span style='color:#8b949e;'>TERMINAL_v2.8</span></h1>", unsafe_allow_html=True)

if user_token:
    df, balance, err = fetch_and_fix_data(user_token)
    
    if df is not None:
        # --- CALCULATE METRICS ---
        now = datetime.now() # Naive current time
        history_sum = df['usd_amount'].sum()
        
        # Comparison now works because both are timezone-naive
        day_ago = now - pd.Timedelta(days=1)
        last_24h = df[df['timestamp'] > day_ago]['usd_amount'].sum()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("ACCOUNT BALANCE", f"${balance:,.2f}")
        m2.metric("ALLOCATED TOTAL", f"${history_sum:,.2f}")
        m3.metric("UNSYNCED/BONUS", f"${max(0, balance - history_sum):,.2f}")
        m4.metric("24H EARNINGS", f"+${last_24h:,.4f}")

        # --- CHARTS ---
        st.markdown("---")
        c1, c2 = st.columns([2, 1])
        with c1:
            daily = df.set_index('timestamp').resample('D')['usd_amount'].sum().reset_index()
            fig = px.area(daily, x='timestamp', y='usd_amount', template="plotly_dark", title="// DAILY_FLOW")
            fig.update_traces(line_color='#00f2ff', fillcolor='rgba(0, 242, 255, 0.1)')
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("### // SYSTEM_LOG")
            st.dataframe(df.sort_values('timestamp', ascending=False)[['timestamp', 'usd_amount']], hide_index=True)

    else:
        st.error(f"📡 SYNC FAILED: {err}")
        if "401" in str(err) or "JWT" in str(err):
            st.warning("Token Expired. Refresh your browser and paste a new Bearer token.")
else:
    st.info("👈 Please enter a fresh Bearer Token in the sidebar.")
