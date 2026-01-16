import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIG ---
BASE_URL = "https://api.unityedge.io/rest/v1/rpc"
URL_ALLOCATIONS = f"{BASE_URL}/rewards_get_allocations"
URL_BALANCE = f"{BASE_URL}/rewards_get_balance"
API_KEY = "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c"

st.set_page_config(page_title="UNITY_CORE // TERMINAL", layout="wide")

# --- THEME ---
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

# --- ROBUST BALANCE PARSER ---
def parse_balance_response(raw_data):
    """Safely extracts a number from almost any JSON format"""
    try:
        # If it's just a number (int or float)
        if isinstance(raw_data, (int, float)):
            return float(raw_data)
        
        # If it's a list: [234000000] or [{"bal": 234000000}]
        if isinstance(raw_data, list) and len(raw_data) > 0:
            item = raw_data[0]
            if isinstance(item, (int, float)): return float(item)
            if isinstance(item, dict): return float(list(item.values())[0])
            
        # If it's a dict: {"balance": 234000000}
        if isinstance(raw_data, dict):
            return float(list(raw_data.values())[0])
            
        return 0.0
    except:
        return 0.0

# --- DATA ENGINE ---
def fetch_core_data(token):
    clean_token = token.strip().replace('Bearer ', '')
    headers = {"apikey": API_KEY, "authorization": f"Bearer {clean_token}", "content-type": "application/json"}
    
    try:
        # 1. Fetch Balance
        r_bal = requests.post(URL_BALANCE, headers=headers, json={}, timeout=10)
        true_bal = parse_balance_response(r_bal.json()) if r_bal.status_code == 200 else 0.0
        
        # 2. Fetch History
        r_alloc = requests.post(URL_ALLOCATIONS, headers=headers, json={"skip": None, "take": None}, timeout=10)
        if r_alloc.status_code != 200:
            return None, 0, f"API Error {r_alloc.status_code}: {r_alloc.text}"
            
        df = pd.DataFrame(r_alloc.json())
        if df.empty:
            return None, true_bal / 1_000_000, "Historical data stream empty."

        # 3. Clean Columns & Timezones
        date_col = next((c for c in df.columns if any(k in c.lower() for k in ['time', 'date', 'created'])), None)
        amt_col = next((c for c in df.columns if any(k in c.lower() for k in ['amount', 'reward'])), None)

        df['timestamp'] = pd.to_datetime(df[date_col], utc=True).dt.tz_localize(None)
        df['usd_amount'] = pd.to_numeric(df[amt_col]) / 1_000_000
        
        return df, true_bal / 1_000_000, None

    except Exception as e:
        return None, 0, f"Engine Error: {str(e)}"

# --- UI RENDER ---
st.markdown("<h1>█ UNITY_CORE <span style='color:#8b949e;'>TERMINAL_v2.9</span></h1>", unsafe_allow_html=True)

if user_token:
    df, balance, err = fetch_core_data(user_token)
    
    if df is not None:
        history_sum = df['usd_amount'].sum()
        bonus_gap = max(0, balance - history_sum)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("TRUE BALANCE", f"${balance:,.2f}")
        m2.metric("HISTORICAL SUM", f"${history_sum:,.2f}")
        m3.metric("BONUS / PENDING", f"${bonus_gap:,.2f}")
        
        # 24h Logic
        day_ago = datetime.now() - pd.Timedelta(days=1)
        last_24h = df[df['timestamp'] > day_ago]['usd_amount'].sum()
        m4.metric("24H VELOCITY", f"+${last_24h:,.4f}")

        st.markdown("---")
        
        # Timeline Chart
        daily = df.set_index('timestamp').resample('D')['usd_amount'].sum().reset_index()
        fig = px.area(daily, x='timestamp', y='usd_amount', template="plotly_dark", title="// ACCUMULATION_TIMELINE")
        fig.update_traces(line_color='#00f2ff', fillcolor='rgba(0, 242, 255, 0.1)')
        st.plotly_chart(fig, use_container_width=True)

        # Log Table
        st.dataframe(df.sort_values('timestamp', ascending=False)[['timestamp', 'usd_amount']], use_container_width=True, hide_index=True)

    else:
        st.error(f"📡 SYNC FAILED: {err}")
        if "401" in str(err): st.warning("TOKEN EXPIRED. REFRESH BROWSER.")
else:
    st.info("👈 Waiting for Bearer Token input in the sidebar.")

# --- DIAGNOSTICS ---
with st.expander("🛠️ SYSTEM DIAGNOSTICS"):
    if user_token:
        st.write("Checking API Responses...")
        h = {"apikey": API_KEY, "authorization": f"Bearer {user_token.strip()}"}
        st.write("Balance Endpoint Raw Data:")
        st.code(requests.post(URL_BALANCE, headers=h, json={}).text)
