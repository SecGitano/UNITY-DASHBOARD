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
    """Truncates ID to 4chars...4chars"""
    s = str(id_val)
    if len(s) > 10:
        return f"{s[:4]}...{s[-4:]}"
    return s

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
        df['date'] = df['timestamp'].dt.date
        df['usd_amount'] = pd.to_numeric(df[a_col]) / 1_000_000
        
        # Apply ID Masking
        df['NODE_ID_FULL'] = df[node_col] # Keep original for grouping
        df['NODE_ID'] = df[node_col].apply(format_id)
        df['LIC_ID'] = df[lic_col].apply(format_id)
        
        return df, true_balance, None
    except Exception as e:
        return None, 0, str(e)

# --- MAIN ---
st.markdown("<h1>█ UNITY_CORE <span style='color:#00f2ff;'>NODE_INTELLIGENCE</span></h1>", unsafe_allow_html=True)

if raw_input:
    df, balance, err = sync_data(raw_input)
    
    if df is not None:
        # --- TOP METRICS ---
        total_nodes = df['NODE_ID_FULL'].nunique()
        total_lics = df['LIC_ID'].nunique()
        node_sum = df['usd_amount'].sum()
        bonus = max(0, balance - node_sum)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("TOTAL BALANCE", f"${balance:,.2f}")
        m2.metric("UNIQUE NODES", total_nodes)
        m3.metric("ACTIVE LICENSES", total_lics)
        m4.metric("BONUS / OTHER", f"${bonus:,.2f}")

        st.markdown("---")

        # --- NODE SUMMARY ---
        st.subheader("// NODE_PERFORMANCE_LOG")
        node_stats = df.groupby('NODE_ID').agg({
            'LIC_ID': 'nunique',
            'usd_amount': 'sum'
        }).reset_index().rename(columns={'LIC_ID': 'Licenses', 'usd_amount': 'Rewards ($)'})
        
        st.dataframe(node_stats.sort_values('Rewards ($)', ascending=False), 
                     column_config={"Rewards ($)": st.column_config.NumberColumn(format="$ %.4f")},
                     hide_index=True, use_container_width=True)

        st.markdown("---")

        # --- 7-DAY MATRIX FIX ---
        st.subheader("// LICENSE_PERFORMANCE_MATRIX (7D)")
        
        # Create dates and string versions for columns
        today = datetime.now().date()
        date_list = [(today - timedelta(days=i)) for i in range(1, 8)]
        date_str_list = [d.strftime('%Y-%m-%d') for d in date_list]
        
        # Lifetime total per License
        lic_total = df.groupby('LIC_ID')['usd_amount'].sum().rename('TOTAL_USD')
        
        # Last 7 Days Pivot
        df_7d = df[df['date'].isin(date_list)].copy()
        if not df_7d.empty:
            pivot_7d = df_7d.pivot_table(index='LIC_ID', columns='date', values='usd_amount', aggfunc='sum').fillna(0)
            # CRITICAL FIX: Convert column names (date objects) to strings
            pivot_7d.columns = [d.strftime('%Y-%m-%d') for d in pivot_7d.columns]
            
            # Merge
            matrix = pd.merge(lic_total, pivot_7d, left_index=True, right_index=True, how='left').fillna(0)
            matrix = matrix.sort_values('TOTAL_USD', ascending=False)
            
            # Build Config
            conf = {"TOTAL_USD": st.column_config.NumberColumn("TOTAL", format="$ %.4f")}
            for ds in date_str_list:
                if ds in matrix.columns:
                    # Clean up the display name to "Jan 16"
                    clean_name = datetime.strptime(ds, '%Y-%m-%d').strftime('%b %d')
                    conf[ds] = st.column_config.NumberColumn(clean_name, format="$ %.4f")

            st.dataframe(matrix, column_config=conf, use_container_width=True)
        else:
            st.info("No activity recorded in the last 7 days.")

        # --- GRAPHIC ---
        st.markdown("---")
        daily_flow = df.set_index('timestamp').resample('D')['usd_amount'].sum().reset_index()
        fig = px.area(daily_flow, x='timestamp', y='usd_amount', template="plotly_dark", title="// ACCUMULATION_VELOCITY")
        fig.update_traces(line_color='#00f2ff', fillcolor='rgba(0, 242, 255, 0.1)')
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.error(f"📡 SYNC ERROR: {err}")
else:
    st.info("👈 Paste Bearer Token in sidebar to initialize terminal.")
