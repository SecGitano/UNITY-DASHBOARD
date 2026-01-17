import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- SYSTEM CONFIG ---
API_URL_BAL = "https://api.unityedge.io/rest/v1/rpc/rewards_get_balance"
API_URL_HIS = "https://api.unityedge.io/rest/v1/rpc/rewards_get_allocations"
API_KEY = "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c"

st.set_page_config(page_title="UNITY_CORE // DEEP_ANALYTICS", layout="wide")

# --- UI THEME ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono&display=swap');
    .stApp { background-color: #0d1117; font-family: 'JetBrains+Mono', monospace; }
    [data-testid="stMetric"] { background: #161b22; border: 1px solid #30363d; border-left: 5px solid #00f2ff; padding: 15px; }
    h1, h2, h3 { font-family: 'Orbitron', sans-serif; color: #f0f6fc; }
    /* Tooltip styling */
    .stTooltipIcon { color: #00f2ff !important; }
    </style>
    """, unsafe_allow_html=True)

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
        return 0.0
    except: return 0.0

# --- DEEP SYNC ENGINE ---
def sync_data(token):
    clean_token = token.strip().replace('Bearer ', '')
    headers = {"apikey": API_KEY, "authorization": f"Bearer {clean_token}", "content-type": "application/json"}
    
    try:
        # 1. Fetch Balance
        r_bal = requests.post(API_URL_BAL, headers=headers, json={}, timeout=10)
        true_balance = parse_balance(r_bal.json()) / 1_000_000

        # 2. Deep Fetch History
        all_records = []
        skip = 0
        batch_size = 1000 
        status_text = st.empty()
        
        while True:
            status_text.text(f"⏳ Deep Sync in progress... (Fetched {skip} records)")
            payload = {"skip": skip, "take": batch_size}
            r_his = requests.post(API_URL_HIS, headers=headers, json=payload, timeout=15)
            batch = r_his.json()
            if not isinstance(batch, list) or len(batch) == 0: break
            all_records.extend(batch)
            if len(batch) < batch_size: break
            skip += batch_size
            
        status_text.empty()
            
        if not all_records: return None, true_balance, "No history found."
        df = pd.DataFrame(all_records)

        # Detect and Cleanup
        d_col = next((c for c in df.columns if 'time' in c or 'created' in c), 'created_at')
        a_col = next((c for c in df.columns if 'amount' in c or 'reward' in c), 'amount')
        node_col = next((c for c in df.columns if 'node' in c.lower()), 'node_id')
        lic_col = next((c for c in df.columns if 'license' in c.lower()), 'license_id')

        df['timestamp'] = pd.to_datetime(df[d_col], utc=True).dt.tz_localize(None)
        df['date_only'] = df['timestamp'].dt.date
        df['usd_amount'] = pd.to_numeric(df[a_col]) / 1_000_000
        
        df['NODE_ID_RAW'] = df[node_col]
        df['NODE_ID'] = df[node_col].apply(format_id)
        df['LIC_ID'] = df[lic_col].apply(format_id)
        
        return df, true_balance, None
        
    except Exception as e:
        return None, 0, f"Engine Failure: {str(e)}"

# --- MAIN RENDER ---
st.markdown("<h1>█ UNITY_CORE <span style='color:#00f2ff;'>DEEP_ANALYTICS</span></h1>", unsafe_allow_html=True)

if raw_input:
    df, balance, err = sync_data(raw_input)
    
    if df is not None:
        # --- TOP METRICS ---
        today = datetime.now().date()
        yesterday_date = today - timedelta(days=1)
        seven_days_ago = today - timedelta(days=7)
        
        rewards_7d = df[df['date_only'] >= seven_days_ago]['usd_amount'].sum()
        yesterday_total = df[df['date_only'] == yesterday_date]['usd_amount'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("TOTAL BALANCE", f"${balance:,.2f}")
        m2.metric("REWARDS LAST 7 DAYS", f"${rewards_7d:,.2f}")
        m3.metric("YESTERDAY'S REWARDS", f"${yesterday_total:,.4f}")

        st.markdown("---")

        # --- NEW CHARTS SECTION ---
        st.subheader("// VISUAL_REWARD_INTELLIGENCE")
        c1, c2 = st.columns(2)

        with c1:
            # Chart 1: Rewards Accumulation Per Day
            daily_acc = df.groupby('date_only')['usd_amount'].sum().reset_index()
            daily_acc['cumulative'] = daily_acc['usd_amount'].cumsum()
            
            fig1 = px.area(daily_acc, x='date_only', y='usd_amount', 
                          title="DAILY REWARD FLOW",
                          labels={'usd_amount': 'USD ($)', 'date_only': 'Date'},
                          template="plotly_dark")
            fig1.update_traces(line_color='#00f2ff', fillcolor='rgba(0, 242, 255, 0.1)')
            fig1.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig1, use_container_width=True)

        with c2:
            # Chart 2: Total Rewards Per Node
            node_rewards = df.groupby('NODE_ID')['usd_amount'].sum().sort_values(ascending=False).reset_index()
            
            fig2 = px.bar(node_rewards, x='NODE_ID', y='usd_amount',
                         title="REWARDS PER NODE",
                         labels={'usd_amount': 'Total USD ($)', 'NODE_ID': 'Node ID'},
                         template="plotly_dark",
                         color='usd_amount',
                         color_continuous_scale='Blues')
            fig2.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")

        # --- NODE PERFORMANCE LOG ---
        st.subheader("// NODE_PERFORMANCE_LOG")
        node_stats = df.groupby('NODE_ID').agg({'LIC_ID': 'nunique','usd_amount': 'sum'}).reset_index().rename(columns={'LIC_ID': 'In Use', 'usd_amount': 'Total'})
        node_stats['Available'] = 200 - node_stats['In Use']
        
        df_7d = df[df['date_only'] >= seven_days_ago]
        node_7d = df_7d.groupby('NODE_ID')['usd_amount'].sum().reset_index().rename(columns={'usd_amount': '7D_Sum'})
        node_stats = pd.merge(node_stats, node_7d, on='NODE_ID', how='left').fillna(0)
        node_stats['Avg / Lic'] = node_stats['Total'] / node_stats['In Use']
        node_stats['Avg Daily (7D)'] = node_stats['7D_Sum'] / 7
        
        st.dataframe(node_stats.sort_values('Total', ascending=False).drop(columns=['7D_Sum']), 
                     column_config={
                         "Total": st.column_config.NumberColumn("TOTAL", format="$ %.4f"), 
                         "Avg / Lic": st.column_config.NumberColumn("AVG / LIC", format="$ %.4f"), 
                         "Avg Daily (7D)": st.column_config.NumberColumn("AVG DAILY (7D)", format="$ %.4f")
                     },
                     hide_index=True, use_container_width=True)

        st.markdown("---")

        # --- 7-DAY MATRIX ---
        st.subheader("// LICENSE_PERFORMANCE_MATRIX (7D)")
        date_list = [(today - timedelta(days=i)) for i in range(1, 8)]
        lic_total = df.groupby('LIC_ID')['usd_amount'].sum().rename('TOTAL_USD')
        pivot_7d = df[df['date_only'].isin(date_list)].pivot_table(index='LIC_ID', columns='date_only', values='usd_amount', aggfunc='sum').fillna(0)
        pivot_7d.columns = [d.strftime('%Y-%m-%d') for d in pivot_7d.columns]
        matrix = pd.merge(lic_total, pivot_7d, left_index=True, right_index=True, how='left').fillna(0)
        conf = {"TOTAL_USD": st.column_config.NumberColumn("LIFETIME TOTAL", format="$ %.4f")}
        for d in date_list:
            ds = d.strftime('%Y-%m-%d'); conf[ds] = st.column_config.NumberColumn(d.strftime('%b %d'), format="$ %.4f")
            
        st.dataframe(matrix.sort_values('TOTAL_USD', ascending=False), column_config=conf, use_container_width=True)

    else:
        st.error(f"📡 SYNC FAILED: {err}")
else:
    st.info("👈 Authentication Required. Paste Bearer Token in sidebar to initialize the Terminal.")
