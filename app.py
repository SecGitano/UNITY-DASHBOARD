import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# --- SYSTEM CONFIG ---
API_URL_BAL = "https://api.unityedge.io/rest/v1/rpc/rewards_get_balance"
API_URL_HIS = "https://api.unityedge.io/rest/v1/rpc/rewards_get_allocations"
API_KEY = "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c"

st.set_page_config(page_title="UNITY_CORE // ANALYTICS", layout="wide")

# --- UI THEME ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono&display=swap');
    .stApp { background-color: #0d1117; font-family: 'JetBrains+Mono', monospace; }
    [data-testid="stMetric"] { background: #161b22; border: 1px solid #30363d; border-left: 5px solid #00f2ff; padding: 15px; }
    h1, h2, h3 { font-family: 'Orbitron', sans-serif; color: #f0f6fc; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.title("🔐 ACCESS CONTROL")
raw_input = st.sidebar.text_area("Paste Bearer Token:", height=100)

# --- BULLETPROOF PARSERS ---
def parse_balance(data):
    """Safely extracts a number regardless of format (int, list, or dict)"""
    try:
        if isinstance(data, (int, float)): return float(data)
        if isinstance(data, list) and len(data) > 0:
            item = data[0]
            if isinstance(item, (int, float)): return float(item)
            if isinstance(item, dict): return float(next(iter(item.values())))
        if isinstance(data, dict): return float(next(iter(data.values())))
        return 0.0
    except: return 0.0

def sync_data(token):
    clean_token = token.strip().replace('Bearer ', '')
    headers = {"apikey": API_KEY, "authorization": f"Bearer {clean_token}", "content-type": "application/json"}
    try:
        # 1. Fetch Balance
        r_bal = requests.post(API_URL_BAL, headers=headers, json={}, timeout=10)
        true_balance = parse_balance(r_bal.json()) / 1_000_000

        # 2. Fetch History
        r_his = requests.post(API_URL_HIS, headers=headers, json={"skip": None, "take": None}, timeout=10)
        df = pd.DataFrame(r_his.json())
        
        # --- COLUMN DETECTION ---
        lic_col = next((c for c in df.columns if 'license' in c.lower()), 'license_id')
        node_col = next((c for c in df.columns if 'node' in c.lower()), 'node_id')
        d_col = next((c for c in df.columns if 'time' in c or 'created' in c), 'created_at')
        a_col = next((c for c in df.columns if 'amount' in c or 'reward' in c), 'amount')

        # Clean types and timezones
        df['timestamp'] = pd.to_datetime(df[d_col], utc=True).dt.tz_localize(None)
        df['date'] = df['timestamp'].dt.date
        df['usd_amount'] = pd.to_numeric(df[a_col]) / 1_000_000
        df = df.rename(columns={lic_col: 'LIC_ID', node_col: 'NODE_ID'})
        
        return df, true_balance, None
    except Exception as e:
        return None, 0, str(e)

# --- MAIN INTERFACE ---
st.markdown("<h1>█ UNITY_CORE <span style='color:#00f2ff;'>NODE_INTELLIGENCE</span></h1>", unsafe_allow_html=True)

if raw_input:
    df, balance, err = sync_data(raw_input)
    
    if df is not None:
        # --- TOP LEVEL METRICS ---
        total_nodes = df['NODE_ID'].nunique()
        total_lics = df['LIC_ID'].nunique()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("ACCOUNT BALANCE", f"${balance:,.2f}")
        m2.metric("TOTAL NODES", total_nodes)
        m3.metric("TOTAL LICENSES", total_lics)
        m4.metric("AVG LIC/NODE", f"{total_lics/total_nodes:.1f}" if total_nodes > 0 else "0")

        st.markdown("---")

        # --- NODE SUMMARY SECTION ---
        st.subheader("// NODE_HARDWARE_OVERVIEW")
        # Grouping by node to see performance per hardware
        node_summary = df.groupby('NODE_ID').agg({
            'LIC_ID': 'nunique',
            'usd_amount': 'sum'
        }).reset_index().rename(columns={'LIC_ID': 'Licenses', 'usd_amount': 'Total Rewards ($)'})
        
        c1, c2 = st.columns([2, 1])
        with c1:
            fig_node = px.bar(node_summary, x='NODE_ID', y='Total Rewards ($)', color='Licenses', 
                             template="plotly_dark", title="Rewards per Node (Colored by License Count)")
            st.plotly_chart(fig_node, use_container_width=True)
        with c2:
            st.dataframe(node_summary.sort_values('Total Rewards ($)', ascending=False), hide_index=True)

        st.markdown("---")

        # --- 7-DAY LICENSE PERFORMANCE MATRIX ---
        st.subheader("// LICENSE_PERFORMANCE_MATRIX")
        
        # Calculate dates
        today = datetime.now().date()
        date_cols = [(today - timedelta(days=i)) for i in range(1, 8)] # Yesterday through 7 days ago
        
        # Build Matrix
        # 1. Total lifetime rewards per license
        lic_total = df.groupby('LIC_ID')['usd_amount'].sum().rename('LIFETIME_USD')
        
        # 2. Pivot daily rewards for the last 7 days
        df_7d = df[df['date'].isin(date_cols)]
        pivot_7d = df_7d.pivot_table(index='LIC_ID', columns='date', values='usd_amount', aggfunc='sum').fillna(0)
        
        # 3. Combine
        matrix = pd.merge(lic_total, pivot_7d, left_index=True, right_index=True, how='right').sort_values('LIFETIME_USD', ascending=False)
        
        # Formatting column names for display
        column_mapping = {d: d.strftime('%b %d') for d in date_cols}
        
        st.dataframe(
            matrix,
            column_config={
                "LIFETIME_USD": st.column_config.NumberColumn("TOTAL_REWARD", format="$ %.4f"),
                **{d: st.column_config.NumberColumn(d.strftime('%b %d'), format="$ %.4f") for d in date_cols}
            },
            use_container_width=True
        )

        # --- REWARD VELOCITY ---
        st.markdown("---")
        st.subheader("// REWARD_VELOCITY_FLOW")
        daily_flow = df.set_index('timestamp').resample('D')['usd_amount'].sum().reset_index()
        fig_flow = px.line(daily_flow, x='timestamp', y='usd_amount', template="plotly_dark")
        fig_flow.update_traces(line_color='#00f2ff')
        st.plotly_chart(fig_flow, use_container_width=True)

    else:
        st.error(f"📡 OFFLINE: {err}")
else:
    st.info("👈 Authentication Required. Paste Bearer Token in sidebar.")
