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

st.set_page_config(page_title="UNITY_CORE // MASTER TERMINAL", layout="wide", page_icon="💠")

# --- UI THEME ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono&display=swap');
    .stApp { background-color: #0d1117; font-family: 'JetBrains+Mono', monospace; }
    
    [data-testid="stMetric"] { background: #161b22; border: 1px solid #30363d; border-left: 5px solid #00f2ff; padding: 15px; box-shadow: 0 0 10px rgba(0, 242, 255, 0.1); }
    [data-testid="stMetricLabel"] { color: #8b949e; font-size: 0.8rem; }
    [data-testid="stMetricValue"] { color: #f0f6fc; font-family: 'Orbitron', sans-serif; font-size: 1.8rem; }
    
    h1, h2, h3 { font-family: 'Orbitron', sans-serif; color: #f0f6fc; text-transform: uppercase; letter-spacing: 2px; }
    .drilldown-box { background: #11151c; border: 1px solid #00f2ff; padding: 25px; border-radius: 5px; margin: 20px 0; }
    
    .status-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 10px; margin-top: 20px; margin-bottom: 20px; }
    .status-box { 
        padding: 15px; text-align: center; border-radius: 4px; 
        font-family: 'Orbitron', sans-serif; font-weight: bold; font-size: 0.9em; 
        cursor: help; transition: all 0.2s; position: relative;
    }
    .status-box:hover { transform: scale(1.1); z-index: 10; box-shadow: 0 0 15px rgba(255,255,255,0.2); }
    
    .status-green { background: rgba(0, 242, 70, 0.1); border: 1px solid #00f246; color: #00f246; box-shadow: inset 0 0 10px rgba(0, 242, 70, 0.2); }
    .status-yellow { background: rgba(255, 215, 0, 0.1); border: 1px solid #ffd700; color: #ffd700; box-shadow: inset 0 0 10px rgba(255, 215, 0, 0.2); }
    .status-red { background: rgba(255, 0, 60, 0.1); border: 1px solid #ff003c; color: #ff003c; box-shadow: inset 0 0 10px rgba(255, 0, 60, 0.2); }
    </style>
    """, unsafe_allow_html=True)

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

def apply_dark_theme(fig):
    fig.update_layout(
        paper_bgcolor='#0d1117', plot_bgcolor='#0d1117',
        font_family="JetBrains Mono", font_color="#8b949e",
        title_font_family="Orbitron", title_font_color="#f0f6fc",
        xaxis=dict(showgrid=True, gridcolor='#30363d', zerolinecolor='#30363d'),
        yaxis=dict(showgrid=True, gridcolor='#30363d', zerolinecolor='#30363d'),
        legend=dict(bgcolor='rgba(0,0,0,0)', bordercolor='#30363d')
    )
    return fig

# --- DATA ENGINE ---
@st.cache_data(ttl=600, show_spinner=False)
def sync_data(token):
    clean_token = token.strip().replace('Bearer ', '')
    headers = {"apikey": API_KEY, "authorization": f"Bearer {clean_token}", "content-type": "application/json"}
    try:
        r_bal = requests.post(API_URL_BAL, headers=headers, json={}, timeout=10)
        true_balance = parse_balance(r_bal.json()) / 1_000_000
        all_records = []; skip = 0; batch_size = 1000 
        placeholder = st.empty()
        while True:
            placeholder.text(f"⏳ SYNCING DEEP HISTORY... PACKET {skip}...")
            r_his = requests.post(API_URL_HIS, headers=headers, json={"skip": skip, "take": batch_size}, timeout=15)
            if r_his.status_code != 200: break
            batch = r_his.json()
            if not isinstance(batch, list) or len(batch) == 0: break
            all_records.extend(batch)
            if len(batch) < batch_size: break
            skip += batch_size
        placeholder.empty()
        if not all_records: return None, true_balance, "No history found."
        df = pd.DataFrame(all_records)
        d_col = next((c for c in df.columns if 'time' in c or 'created' in c), 'created_at')
        a_col = next((c for c in df.columns if 'amount' in c or 'reward' in c), 'amount')
        node_col = next((c for c in df.columns if 'node' in c.lower()), 'node_id')
        lic_col = next((c for c in df.columns if 'license' in c.lower()), 'license_id')
        df['timestamp'] = pd.to_datetime(df[d_col], utc=True).dt.tz_localize(None)
        df['date_only'] = df['timestamp'].dt.date
        df['usd_amount'] = pd.to_numeric(df[a_col]) / 1_000_000
        df['NODE_RAW'] = df[node_col]; df['LIC_RAW'] = df[lic_col]
        df['NODE_ID'] = df['NODE_RAW'].apply(format_id); df['LIC_ID'] = df['LIC_RAW'].apply(format_id)
        return df, true_balance, None
    except Exception as e: return None, 0, str(e)

# --- SIDEBAR ---
st.sidebar.title("🔐 ACCESS CONTROL")
raw_input = st.sidebar.text_area("Paste Bearer Token:", height=100)

# --- MAIN ---
if raw_input:
    df, balance, err = sync_data(raw_input)
    if df is not None:
        today = datetime.now().date(); s_days = today - timedelta(days=7)
        r_7d = df[df['date_only'] >= s_days]['usd_amount'].sum()
        y_total = df[df['date_only'] == (today - timedelta(days=1))]['usd_amount'].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("TOTAL BALANCE", f"${balance:,.2f}")
        m2.metric("REWARDS LAST 7 DAYS", f"${r_7d:,.2f}")
        m3.metric("YESTERDAY'S REWARDS", f"${y_total:,.4f}")

        # --- PERFORMANCE HEATMAP (WITH NEW 0.02 FILTER) ---
        st.markdown("---")
        st.subheader("// PERFORMANCE_HEATMAP (BASELINE: $0.02 - $5.00)")
        unique_lics = sorted(df['LIC_RAW'].unique())
        now = datetime.now()
        
        lic_stats = []
        for lic in unique_lics:
            subset = df[df['LIC_RAW'] == lic]
            first_seen = subset['timestamp'].min()
            days_active = max(1, (now - first_seen).days)
            # Apply Filter: Remove > $5 and < $0.02
            refined_subset = subset[(subset['usd_amount'] <= 5.0) & (subset['usd_amount'] >= 0.02)]
            avg = refined_subset['usd_amount'].sum() / days_active
            lic_stats.append({'lic': lic, 'avg': avg})
        
        stats_df = pd.DataFrame(lic_stats)
        min_avg, max_avg = stats_df['avg'].min(), stats_df['avg'].max()
        
        html_heat = '<div class="status-grid">'
        for i, row in stats_df.iterrows():
            score = 1.0 if (max_avg - min_avg) == 0 else (row['avg'] - min_avg) / (max_avg - min_avg)
            hue = int(score * 9) * (120 / 9)
            style = f"background: hsla({hue}, 100%, 50%, 0.15); border: 1px solid hsl({hue}, 100%, 50%); color: hsl({hue}, 100%, 75%);"
            tooltip = f"ID: {format_id(row['lic'])} &#10;Filtered Avg: ${row['avg']:.4f}/day"
            html_heat += f'<div class="status-box" style="{style}" title="{tooltip}">#{i+1}</div>'
        html_heat += '</div>'
        st.markdown(html_heat, unsafe_allow_html=True)

        # --- CHARTS (WITH REFINED BASELINE) ---
        st.markdown("---")
        st.subheader("// VISUAL_ANALYTICS")
        c1, c2 = st.columns(2)
        with c1:
            tx_vol = df.groupby('date_only').size().reset_index(name='tx')
            st.plotly_chart(apply_dark_theme(px.bar(tx_vol, x='date_only', y='tx', title="TX VOLUME", template="plotly_dark")), use_container_width=True)
        with c2:
            # Chart Filter: Exclude < 0.02 and > 5.00
            refined_df = df[(df['usd_amount'] <= 5.0) & (df['usd_amount'] >= 0.02)]
            daily_avg = refined_df.groupby('date_only')['usd_amount'].mean().reset_index()
            fig_avg = px.area(daily_avg, x='date_only', y='usd_amount', title="BASELINE AVG ($0.02 - $5.00)")
            fig_avg.update_traces(line_color='#d000ff', fillcolor='rgba(208, 0, 255, 0.1)')
            st.plotly_chart(apply_dark_theme(fig_avg), use_container_width=True)

        # --- NODE LOG ---
        st.markdown("---")
        st.subheader("// NODE_PERFORMANCE_LOG")
        node_stats = df.groupby('NODE_ID').agg({'LIC_RAW': 'nunique','usd_amount': 'sum'}).reset_index().rename(columns={'LIC_RAW': 'In Use', 'usd_amount': 'Total'})
        node_stats['Available'] = 200 - node_stats['In Use']
        node_7d = df[df['date_only'] >= s_days].groupby('NODE_ID')['usd_amount'].sum().reset_index().rename(columns={'usd_amount': '7D_Sum'})
        node_stats = pd.merge(node_stats, node_7d, on='NODE_ID', how='left').fillna(0)
        node_stats['Avg / Lic'] = node_stats['Total'] / node_stats['In Use']
        node_stats['Avg Daily (7D)'] = node_stats['7D_Sum'] / 7
        st.dataframe(node_stats.sort_values('Total', ascending=False).drop(columns=['7D_Sum']), hide_index=True, use_container_width=True)

        # --- MATRIX (BOTTOM) ---
        st.markdown("---")
        st.subheader("// PERFORMANCE_MATRIX (7D)")
        d_list = [(today - timedelta(days=i)) for i in range(1, 8)]
        lic_tot = df.groupby('LIC_RAW')['usd_amount'].sum().rename('TOTAL_USD').reset_index()
        p_7d = df[df['date_only'].isin(d_list)].pivot_table(index='LIC_RAW', columns='date_only', values='usd_amount', aggfunc='sum').fillna(0)
        p_7d.columns = [d.strftime('%Y-%m-%d') for d in p_7d.columns]
        matrix = pd.merge(lic_tot, p_7d, on='LIC_RAW', how='left').fillna(0).sort_values('TOTAL_USD', ascending=False)
        matrix['LIC_RAW'] = matrix['LIC_RAW'].apply(format_id)
        conf = {"LIC_RAW": "LICENSE_ID", "TOTAL_USD": st.column_config.NumberColumn("TOTAL", format="$ %.4f")}
        for d in d_list: ds = d.strftime('%Y-%m-%d'); conf[ds] = st.column_config.NumberColumn(d.strftime('%b %d'), format="$ %.4f")
        st.dataframe(matrix, column_config=conf, use_container_width=True, hide_index=True)

    else: st.error(f"📡 SYNC FAILED: {err}")
else: st.info("👈 Authentication Required. Paste Bearer Token in sidebar.")
