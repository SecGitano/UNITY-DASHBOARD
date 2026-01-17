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

st.set_page_config(page_title="UNITY_CORE // ADVANCED_ANALYTICS", layout="wide")

# --- UI THEME ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono&display=swap');
    .stApp { background-color: #0d1117; font-family: 'JetBrains+Mono', monospace; }
    [data-testid="stMetric"] { background: #161b22; border: 1px solid #30363d; border-left: 5px solid #00f2ff; padding: 15px; }
    h1, h2, h3 { font-family: 'Orbitron', sans-serif; color: #f0f6fc; }
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

# --- ADVANCED DAILY CALCULATOR (REMOVES OUTLIERS FROM PEAK & AVG) ---
def process_daily_efficiency(group):
    """Refines both Peak and Average by removing rewards > 5x daily mean."""
    rewards = group['usd_amount']
    if rewards.empty:
        return pd.Series({'refined_peak': 0.0, 'refined_avg': 0.0})
    
    # Calculate base stats for outlier detection
    initial_mean = rewards.mean()
    threshold = initial_mean * 5
    unique_lic_count = group['LIC_ID_RAW'].nunique()
    
    # 1. Refined Peak: Get max that isn't an outlier, or 2nd max if 1st is outlier
    sorted_unique_vals = sorted(rewards.unique(), reverse=True)
    max_val = sorted_unique_vals[0]
    refined_peak = max_val
    if len(sorted_unique_vals) > 1 and max_val > threshold:
        refined_peak = sorted_unique_vals[1]
    
    # 2. Refined Average: Remove all rewards > threshold from the calculation
    filtered_rewards = rewards[rewards <= threshold]
    # Sum only stable rewards and divide by total active licenses of that day
    refined_avg = filtered_rewards.sum() / unique_lic_count if unique_lic_count > 0 else 0.0
    
    return pd.Series({'refined_peak': refined_peak, 'refined_avg': refined_avg})

# --- DEEP SYNC ENGINE ---
def sync_data(token):
    clean_token = token.strip().replace('Bearer ', '')
    headers = {"apikey": API_KEY, "authorization": f"Bearer {clean_token}", "content-type": "application/json"}
    try:
        r_bal = requests.post(API_URL_BAL, headers=headers, json={}, timeout=10)
        true_balance = parse_balance(r_bal.json()) / 1_000_000
        all_records = []; skip = 0; batch_size = 1000 
        status_text = st.empty()
        while True:
            status_text.text(f"⏳ Deep Sync in progress... ({skip} records fetched)")
            r_his = requests.post(API_URL_HIS, headers=headers, json={"skip": skip, "take": batch_size}, timeout=15)
            batch = r_his.json()
            if not isinstance(batch, list) or len(batch) == 0: break
            all_records.extend(batch)
            if len(batch) < batch_size: break
            skip += batch_size
        status_text.empty()
        if not all_records: return None, true_balance, "No history found."
        df = pd.DataFrame(all_records)
        d_col = next((c for c in df.columns if 'time' in c or 'created' in c), 'created_at')
        a_col = next((c for c in df.columns if 'amount' in c or 'reward' in c), 'amount')
        node_col = next((c for c in df.columns if 'node' in c.lower()), 'node_id')
        lic_col = next((c for c in df.columns if 'license' in c.lower()), 'license_id')
        df['timestamp'] = pd.to_datetime(df[d_col], utc=True).dt.tz_localize(None)
        df['date_only'] = df['timestamp'].dt.date
        df['usd_amount'] = pd.to_numeric(df[a_col]) / 1_000_000
        df['NODE_ID'] = df[node_col].apply(format_id)
        df['LIC_ID_RAW'] = df[lic_col]
        df['LIC_ID'] = df[lic_col].apply(format_id)
        return df, true_balance, None
    except Exception as e: return None, 0, str(e)

# --- MAIN RENDER ---
st.markdown("<h1>█ UNITY_CORE <span style='color:#00f2ff;'>ADVANCED_ANALYTICS</span></h1>", unsafe_allow_html=True)

if raw_input:
    df, balance, err = sync_data(raw_input)
    if df is not None:
        today = datetime.now().date(); yest_d = today - timedelta(days=1); s_days = today - timedelta(days=7)
        r_7d = df[df['date_only'] >= s_days]['usd_amount'].sum()
        y_total = df[df['date_only'] == yest_d]['usd_amount'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("TOTAL BALANCE", f"${balance:,.2f}")
        m2.metric("REWARDS LAST 7 DAYS", f"${r_7d:,.2f}")
        m3.metric("YESTERDAY'S REWARDS", f"${y_total:,.4f}")

        st.markdown("---")

        # --- ROW 1: REWARD FLOW & NODES ---
        c1, c2 = st.columns(2)
        with c1:
            daily_acc = df.groupby('date_only')['usd_amount'].sum().reset_index()
            fig1 = px.area(daily_acc, x='date_only', y='usd_amount', title="DAILY REWARD FLOW", template="plotly_dark")
            fig1.update_traces(line_color='#00f2ff', fillcolor='rgba(0, 242, 255, 0.1)')
            st.plotly_chart(fig1, use_container_width=True)
        with c2:
            node_rew = df.groupby('NODE_ID')['usd_amount'].sum().sort_values(ascending=False).reset_index()
            fig2 = px.bar(node_rew, x='NODE_ID', y='usd_amount', title="REWARDS PER NODE", template="plotly_dark", color='usd_amount', color_continuous_scale='Blues')
            st.plotly_chart(fig2, use_container_width=True)

        # --- ROW 2: VOLUME & EFFICIENCY ---
        c3, c4 = st.columns(2)
        with c3:
            tx_vol = df.groupby('date_only').size().reset_index(name='tx_count')
            fig3 = px.bar(tx_vol, x='date_only', y='tx_count', title="TRANSACTIONS VOLUME", template="plotly_dark")
            fig3.update_traces(marker_color='#7000ff')
            st.plotly_chart(fig3, use_container_width=True)

        with c4:
            # APPLY THE REFINED EFFICIENCY LOGIC
            efficiency_metrics = df.groupby('date_only').apply(process_daily_efficiency).reset_index()

            fig4 = go.Figure()
            # Plot Refined Peak
            fig4.add_trace(go.Scatter(x=efficiency_metrics['date_only'], y=efficiency_metrics['refined_peak'], 
                                     name='Refined Peak (Luck Suppressed)', line=dict(color='#ff00ff', width=2)))
            # Plot Refined Average
            fig4.add_trace(go.Scatter(x=efficiency_metrics['date_only'], y=efficiency_metrics['refined_avg'], 
                                     name='Refined Avg (Outliers Excluded)', line=dict(color='#00f2ff', width=2, dash='dot')))
            
            fig4.update_layout(title="CLEANED EFFICIENCY: PEAK VS AVG", template="plotly_dark", 
                              plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', 
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig4, use_container_width=True)

        st.markdown("---")

        # --- TABLES & MATRIX ---
        node_stats = df.groupby('NODE_ID').agg({'LIC_ID_RAW': 'nunique','usd_amount': 'sum'}).reset_index().rename(columns={'LIC_ID_RAW': 'In Use', 'usd_amount': 'Total'})
        node_stats['Available'] = 200 - node_stats['In Use']
        node_7d = df[df['date_only'] >= s_days].groupby('NODE_ID')['usd_amount'].sum().reset_index().rename(columns={'usd_amount': '7D_Sum'})
        node_stats = pd.merge(node_stats, node_7d, on='NODE_ID', how='left').fillna(0)
        node_stats['Avg / Lic'] = node_stats['Total'] / node_stats['In Use']
        node_stats['Avg Daily (7D)'] = node_stats['7D_Sum'] / 7
        st.dataframe(node_stats.sort_values('Total', ascending=False).drop(columns=['7D_Sum']), column_config={"Total": st.column_config.NumberColumn(format="$ %.4f"), "Avg / Lic": st.column_config.NumberColumn(format="$ %.4f"), "Avg Daily (7D)": st.column_config.NumberColumn(format="$ %.4f")}, hide_index=True, use_container_width=True)

        d_list = [(today - timedelta(days=i)) for i in range(1, 8)]
        lic_tot = df.groupby('LIC_ID')['usd_amount'].sum().rename('TOTAL_USD')
        p_7d = df[df['date_only'].isin(d_list)].pivot_table(index='LIC_ID', columns='date_only', values='usd_amount', aggfunc='sum').fillna(0)
        p_7d.columns = [d.strftime('%Y-%m-%d') for d in p_7d.columns]
        mat = pd.merge(lic_tot, p_7d, left_index=True, right_index=True, how='left').fillna(0).sort_values('TOTAL_USD', ascending=False)
        conf = {"TOTAL_USD": st.column_config.NumberColumn("TOTAL", format="$ %.4f")}
        for d in d_list:
            ds = d.strftime('%Y-%m-%d'); conf[ds] = st.column_config.NumberColumn(d.strftime('%b %d'), format="$ %.4f")
        st.dataframe(mat, column_config=conf, use_container_width=True)
    else: st.error(f"📡 SYNC FAILED: {err}")
else: st.info("👈 Authentication Required. Paste Bearer Token in sidebar.")
