import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- SETTINGS ---
BASE_URL = "https://api.unityedge.io/rest/v1/rpc"
URL_ALLOCATIONS = f"{BASE_URL}/rewards_get_allocations"
URL_BALANCE = f"{BASE_URL}/rewards_get_balance"
API_KEY_STATIC = "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c"

st.set_page_config(page_title="UNITY_CORE // TERMINAL", layout="wide")

# --- CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono&display=swap');
    .stApp { background-color: #0d1117; font-family: 'JetBrains+Mono', monospace; }
    [data-testid="stMetric"] { background: #161b22; border: 1px solid #30363d; border-left: 5px solid #00f2ff; padding: 20px; }
    h1, h2, h3 { font-family: 'Orbitron', sans-serif; color: #f0f6fc; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.title("🔐 AUTHENTICATION")
st.sidebar.info("Tokens expire every 60 minutes. Refresh your browser to get a new one.")
user_token = st.sidebar.text_area("Paste Bearer Token:", height=150)

def fetch_data(token):
    headers = {
        "authority": "api.unityedge.io",
        "apikey": API_KEY_STATIC,
        "authorization": f"Bearer {token.strip().replace('Bearer ', '')}",
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0"
    }
    try:
        # Request Allocations
        r_alloc = requests.post(URL_ALLOCATIONS, headers=headers, json={"skip": None, "take": None}, timeout=10)
        # Request Balance
        r_bal = requests.post(URL_BALANCE, headers=headers, json={}, timeout=10)
        
        if r_alloc.status_code != 200:
            return None, 0, f"Allocations API Error ({r_alloc.status_code}): {r_alloc.text}"
        
        raw_alloc = r_alloc.json()
        if not isinstance(raw_alloc, list) or len(raw_alloc) == 0:
            return None, 0, "No allocation data found. Your token might be expired or the account has no history."

        df = pd.DataFrame(raw_alloc)
        
        # --- SMART COLUMN DETECTION ---
        # Instead of 'created_at', we look for any column with 'time' or 'date'
        date_col = next((c for c in df.columns if any(k in c.lower() for k in ['time', 'date', 'created'])), None)
        # Instead of 'amount', we look for 'amount', 'reward', or 'value'
        amt_col = next((c for c in df.columns if any(k in c.lower() for k in ['amount', 'reward', 'value'])), None)

        if not date_col or not amt_col:
            return None, 0, f"Could not find data columns. Found: {list(df.columns)}"

        df['timestamp'] = pd.to_datetime(df[date_col])
        df['usd_amount'] = pd.to_numeric(df[amt_col]) / 1_000_000
        
        # Parse Balance
        bal_data = r_bal.json()
        try:
            true_bal = float(list(bal_data[0].values())[0] if isinstance(bal_data, list) else list(bal_data.values())[0]) / 1_000_000
        except:
            true_bal = df['usd_amount'].sum() # Fallback

        return df, true_bal, None
    except Exception as e:
        return None, 0, f"System Error: {str(e)}"

# --- MAIN ---
st.markdown("<h1>█ UNITY_CORE <span style='color:#8b949e;'>TERMINAL_v2.7</span></h1>", unsafe_allow_html=True)

if user_token:
    df, true_total, error_msg = fetch_data(user_token)
    
    if df is not None:
        # Dashboard logic
        node_sum = df['usd_amount'].sum()
        bonus = max(0, true_total - node_sum)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("TOTAL BALANCE", f"${true_total:,.2f}")
        m2.metric("NODE REWARDS", f"${node_sum:,.2f}")
        m3.metric("OTHER/BONUS", f"${bonus:,.2f}")
        
        last_24 = df[df['timestamp'] > (datetime.now() - pd.Timedelta(days=1))]['usd_amount'].sum()
        m4.metric("24H VELOCITY", f"+${last_24:,.4f}")

        st.markdown("---")
        c1, c2 = st.columns([2, 1])
        with c1:
            daily = df.set_index('timestamp').resample('D')['usd_amount'].sum().reset_index()
            fig = px.area(daily, x='timestamp', y='usd_amount', template="plotly_dark", title="// FLOW")
            fig.update_traces(line_color='#00f2ff', fillcolor='rgba(0, 242, 255, 0.1)')
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig_pie = go.Figure(data=[go.Pie(labels=['Nodes', 'Bonus'], values=[node_sum, bonus], hole=.5)])
            fig_pie.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', showlegend=False, title="// COMP")
            fig_pie.update_traces(marker=dict(colors=['#00f2ff', '#7000ff']))
            st.plotly_chart(fig_pie, use_container_width=True)

        st.dataframe(df.sort_values('timestamp', ascending=False), use_container_width=True)
    else:
        st.error("📡 SYNC ERROR")
        st.warning(error_msg)
        with st.expander("🛠️ TECHNICAL DIAGNOSTICS"):
            st.write("If you see an empty list below, your token is likely invalid or expired.")
            headers = {"apikey": API_KEY_STATIC, "authorization": f"Bearer {user_token.strip()}"}
            debug_r = requests.post(URL_ALLOCATIONS, headers=headers, json={"skip": None, "take": None})
            st.write("Raw Server Response:")
            st.code(debug_r.text)
else:
    st.info("👈 Paste a fresh Bearer Token into the sidebar to start the terminal.")
