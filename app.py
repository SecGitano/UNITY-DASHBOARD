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

st.set_page_config(page_title="UNITY_CORE // COMMAND", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono&display=swap');
    .stApp { background-color: #0d1117; font-family: 'JetBrains+Mono', monospace; }
    [data-testid="stMetric"] { background: #161b22; border: 1px solid #30363d; border-left: 5px solid #00f2ff; padding: 20px; }
    h1, h2, h3 { font-family: 'Orbitron', sans-serif; color: #f0f6fc; }
    .stTextInput > div > div > input { background-color: #161b22; color: #00f2ff; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR FOR TOKEN ---
st.sidebar.title("🔐 AUTHENTICATION")
user_token = st.sidebar.text_area("Paste Bearer Token here:", height=150, help="Copy the long string after 'Bearer ' from your browser Network tab.")

# --- DATA FETCHING FUNCTION ---
def fetch_unity_data(token):
    headers = {
        "authority": "api.unityedge.io",
        "apikey": API_KEY_STATIC,
        "authorization": f"Bearer {token.replace('Bearer ', '')}",
        "content-type": "application/json",
        "user-agent": "Mozilla/5.0"
    }
    try:
        r_alloc = requests.post(URL_ALLOCATIONS, headers=headers, json={"skip": None, "take": None}, timeout=10)
        r_bal = requests.post(URL_BALANCE, headers=headers, json={}, timeout=10)
        
        if r_alloc.status_code == 200 and r_bal.status_code == 200:
            df = pd.DataFrame(r_alloc.json())
            df['timestamp'] = pd.to_datetime(df['created_at'])
            df['usd_amount'] = pd.to_numeric(df['amount']) / 1_000_000
            
            bal_data = r_bal.json()
            true_bal = float(list(bal_data[0].values())[0] if isinstance(bal_data, list) else list(bal_data.values())[0]) / 1_000_000
            return df, true_bal, None
        else:
            return None, 0, f"Error {r_alloc.status_code}: {r_alloc.text}"
    except Exception as e:
        return None, 0, str(e)

# --- MAIN LOGIC ---
st.markdown("<h1>█ UNITY_CORE <span style='color:#8b949e;'>TERMINAL_v2.6</span></h1>", unsafe_allow_html=True)

if user_token:
    df, true_total, error_msg = fetch_unity_data(user_token)
    
    if df is not None:
        # --- METRICS ---
        m1, m2, m3, m4 = st.columns(4)
        node_sum = df['usd_amount'].sum()
        bonus = true_total - node_sum
        
        m1.metric("TOTAL BALANCE", f"${true_total:,.2f}")
        m2.metric("NODE REWARDS", f"${node_sum:,.2f}")
        m3.metric("OTHER/BONUS", f"${bonus:,.2f}")
        
        last_24 = df[df['timestamp'] > (datetime.now() - pd.Timedelta(days=1))]['usd_amount'].sum()
        m4.metric("24H VELOCITY", f"+${last_24:,.4f}")

        # --- CHARTS ---
        st.markdown("---")
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown("### // ACCUMULATION_FLOW")
            daily = df.set_index('timestamp').resample('D')['usd_amount'].sum().reset_index()
            fig = px.area(daily, x='timestamp', y='usd_amount', template="plotly_dark")
            fig.update_traces(line_color='#00f2ff', fillcolor='rgba(0, 242, 255, 0.1)')
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("### // COMPOSITION")
            fig_pie = go.Figure(data=[go.Pie(labels=['Nodes', 'Bonus'], values=[node_sum, bonus], hole=.5)])
            fig_pie.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
            fig_pie.update_traces(marker=dict(colors=['#00f2ff', '#7000ff']))
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- TABLE ---
        st.dataframe(df.sort_values('timestamp', ascending=False), use_container_width=True, hide_index=True)

    else:
        st.error("📡 CONNECTION FAILED")
        st.warning(f"Message: {error_msg}")
        if "JWT expired" in str(error_msg):
            st.info("💡 Your token expired. Please refresh the Unity website and copy the new Bearer string.")
else:
    st.info("👈 Please enter a fresh Bearer Token in the sidebar to begin syncing.")
