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

# --- UTILITIES ---
def format_id(id_val):
    s = str(id_val)
    return f"{s[:4]}...{s[-4:]}" if len(s) > 10 else s

def parse_balance(data):
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
        # 1. Balance
        r_bal = requests.post(API_URL_BAL, headers=headers, json={}, timeout=10)
        true_balance = parse_balance(r_bal.json()) / 1_000_000

        # 2. History
        r_his = requests.post(API_URL_HIS, headers=headers, json={"skip": None, "take": None}, timeout=10)
        df = pd.DataFrame(r_his.json())
        
        # Clean Columns
        lic_col = next((c for c in df.columns if 'license' in c.lower()), 'license_id')
        node_col = next((c for c in df.columns if 'node' in c.lower()), 'node_id')
        d_col = next((c for c in df.columns if 'time' in c or 'created' in c), 'created_at')
        a_col = next((c for c in df.columns if 'amount' in c or 'reward' in c), 'amount')

        df['timestamp'] = pd.to_datetime(df[d_col], utc=True).dt.tz_localize(None)
        df['usd_amount'] = pd.to_numeric(df[a_col]) / 1_000_000
        
        # Keep full IDs for math, formatted for display
        df['NODE_ID_RAW'] = df[node_col]
        df['NODE_ID'] = df[node_col].apply(format_id)
        df['LIC_ID_RAW'] = df[lic_col]
        df['LIC_ID'] = df[lic_col].apply(format_id)
        
        return df, true_balance, None
    except Exception as e:
        return None, 0, str(e)

# --- MAIN ---
st.markdown("<h1>█ UNITY_CORE <span style='color:#00f2ff;'>NODE_INTELLIGENCE</span></h1>", unsafe_allow_html=True)

if raw_input:
    df, balance, err = sync_data(raw_input)
    
    if df is not None:
        # --- CALCULATIONS ---
        now = datetime.now()
        seven_days_ago = now - timedelta(days=7)
        
        # 7-Day Rewards Sum
        rewards_7d = df[df['timestamp'] >= seven_days_ago]['usd_amount'].sum()
        history_total = df['usd_amount'].sum()
        
        # TOP METRICS
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("TOTAL BALANCE", f"${balance:,.2f}")
        m2.metric("HISTORY TOTAL", f"${history_total:,.2f}")
        
        # "REWARDS LAST 7 DAYS" - Calculation: Balance - (Balance minus last 7 days of recorded rewards)
        # Essentially showing the 7-day delta in this slot as requested.
        m3.metric("REWARDS LAST 7 DAYS", f"${rewards_7d:,.2f}")
        
        # 24H Earning
        yesterday = now - timedelta(days=1)
        last_24h = df[df['timestamp'] >= yesterday]['usd_amount'].sum()
        m4.metric("24H VELOCITY", f"+${last_24h:,.4f}")

        st.markdown("---")

        # --- NODE PERFORMANCE LOG ---
        st.subheader("// NODE_PERFORMANCE_LOG")
        
        # 1. Filter for 7 days
        df_7d = df[df['timestamp'] >= seven_days_ago]
        
        # 2. Build grouped stats
        node_stats = df.groupby('NODE_ID').agg({
            'LIC_ID_RAW': 'nunique',
            'usd_amount': 'sum'
        }).reset_index().rename(columns={'LIC_ID_RAW': 'Licenses', 'usd_amount': 'Total Rewards ($)'})
        
        # 3. Calculate 7-day total per node
        node_7d = df_7d.groupby('NODE_ID')['usd_amount'].sum().reset_index().rename(columns={'usd_amount': '7D_Total'})
        
        # 4. Merge and calculate averages
        node_stats = pd.merge(node_stats, node_7d, on='NODE_ID', how='left').fillna(0)
        
        node_stats['Avg / License'] = node_stats['Total Rewards ($)'] / node_stats['Licenses']
        node_stats['Avg / Day (7D)'] = node_stats['7D_Total'] / 7
        
        st.dataframe(
            node_stats.sort_values('Total Rewards ($)', ascending=False),
            column_config={
                "Total Rewards ($)": st.column_config.NumberColumn("TOTAL", format="$ %.4f"),
                "Avg / License": st.column_config.NumberColumn("AVG / LIC", format="$ %.4f"),
                "Avg / Day (7D)": st.column_config.NumberColumn("AVG DAILY (7D)", format="$ %.4f")
            },
            hide_index=True, use_container_width=True
        )

        st.markdown("---")

        # --- 7-DAY MATRIX (License Table) ---
        st.subheader("// LICENSE_PERFORMANCE_MATRIX (7D)")
        
        today_date = now.date()
        date_list = [(today_date - timedelta(days=i)) for i in range(1, 8)]
        
        lic_total = df.groupby('LIC_ID')['usd_amount'].sum().rename('TOTAL_USD')
        df['date_only'] = df['timestamp'].dt.date
        pivot_7d = df[df['date_only'].isin(date_list)].pivot_table(
            index='LIC_ID', columns='date_only', values='usd_amount', aggfunc='sum'
        ).fillna(0)
        
        # String conversion for column names to prevent Streamlit crash
        pivot_7d.columns = [d.strftime('%Y-%m-%d') for d in pivot_7d.columns]
        matrix = pd.merge(lic_total, pivot_7d, left_index=True, right_index=True, how='left').fillna(0)
        
        conf = {"TOTAL_USD": st.column_config.NumberColumn("TOTAL", format="$ %.4f")}
        for d in date_list:
            ds = d.strftime('%Y-%m-%d')
            if ds in matrix.columns:
                conf[ds] = st.column_config.NumberColumn(d.strftime('%b %d'), format="$ %.4f")

        st.dataframe(matrix.sort_values('TOTAL_USD', ascending=False), column_config=conf, use_container_width=True)

    else:
        st.error(f"📡 SYNC ERROR: {err}")
else:
    st.info("👈 Paste Bearer Token in sidebar to sync your node data.")
