import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 1. SYSTEM CONFIGURATION ---
API_URL_BAL = "https://api.unityedge.io/rest/v1/rpc/rewards_get_balance"
API_URL_HIS = "https://api.unityedge.io/rest/v1/rpc/rewards_get_allocations"
API_KEY = "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c"

st.set_page_config(page_title="UNITY_CORE // COMMAND CENTER", layout="wide", page_icon="💠")

# --- 2. CYBER-INDUSTRIAL UI THEME ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono&display=swap');
    .stApp { background-color: #0d1117; font-family: 'JetBrains+Mono', monospace; }
    
    /* KPI Metrics */
    [data-testid="stMetric"] { 
        background: #161b22; border: 1px solid #30363d; border-left: 5px solid #00f2ff; 
        padding: 15px; box-shadow: 0 0 15px rgba(0, 242, 255, 0.05); 
    }
    [data-testid="stMetricLabel"] { color: #8b949e; font-size: 0.85rem; text-transform: uppercase; }
    [data-testid="stMetricValue"] { color: #f0f6fc; font-family: 'Orbitron', sans-serif; }
    
    /* Typography */
    h1, h2, h3 { font-family: 'Orbitron', sans-serif; color: #f0f6fc; text-transform: uppercase; letter-spacing: 2px; }
    .stMarkdown { color: #8b949e; }
    
    /* Component Styling */
    .drilldown-box { background: #11151c; border: 1px solid #00f2ff; padding: 25px; border-radius: 4px; margin: 20px 0; }
    .status-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(65px, 1fr)); gap: 8px; margin: 15px 0; }
    .status-box { 
        padding: 12px 5px; text-align: center; border-radius: 3px; 
        font-family: 'Orbitron', sans-serif; font-weight: bold; font-size: 0.8em; 
        cursor: help; transition: 0.2s;
    }
    .status-box:hover { transform: scale(1.1); z-index: 5; box-shadow: 0 0 10px rgba(0,242,255,0.3); }
    
    /* Heartbeat Colors */
    .bg-green { background: rgba(0, 242, 70, 0.1); border: 1px solid #00f246; color: #00f246; }
    .bg-yellow { background: rgba(255, 215, 0, 0.1); border: 1px solid #ffd700; color: #ffd700; }
    .bg-red { background: rgba(255, 0, 60, 0.1); border: 1px solid #ff003c; color: #ff003c; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. UTILITIES ---
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

def apply_chart_style(fig):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font_family="JetBrains Mono", font_color="#8b949e",
        title_font_family="Orbitron", title_font_color="#f0f6fc",
        xaxis=dict(showgrid=True, gridcolor='#21262d'),
        yaxis=dict(showgrid=True, gridcolor='#21262d'),
        legend=dict(bgcolor='rgba(0,0,0,0)', bordercolor='#30363d')
    )
    return fig

# --- 4. DATA ENGINE (DEEP SYNC) ---
@st.cache_data(ttl=600, show_spinner=False)
def deep_sync(token):
    clean_token = token.strip().replace('Bearer ', '')
    headers = {"apikey": API_KEY, "authorization": f"Bearer {clean_token}", "content-type": "application/json"}
    
    try:
        # Fetch Balance
        r_bal = requests.post(API_URL_BAL, headers=headers, json={}, timeout=10)
        true_balance = parse_balance(r_bal.json()) / 1_000_000
        
        # Paginated History Fetch
        all_recs = []; skip = 0; batch = 1000
        sync_status = st.empty()
        while True:
            sync_status.text(f"⏳ LINKING CORE... SYNCING PACKET {skip}...")
            r_his = requests.post(API_URL_HIS, headers=headers, json={"skip": skip, "take": batch}, timeout=15)
            if r_his.status_code != 200: break
            data = r_his.json()
            if not isinstance(data, list) or not data: break
            all_recs.extend(data)
            if len(data) < batch: break
            skip += batch
        sync_status.empty()
        
        if not all_recs: return None, true_balance, "History stream empty."
        
        df = pd.DataFrame(all_recs)
        d_col = next((c for c in df.columns if 'time' in c or 'created' in c), 'created_at')
        a_col = next((c for c in df.columns if 'amount' in c or 'reward' in c), 'amount')
        node_col = next((c for c in df.columns if 'node' in c.lower()), 'node_id')
        lic_col = next((c for c in df.columns if 'license' in c.lower()), 'license_id')
        wall_col = next((c for c in df.columns if 'wallet' in c.lower() or 'address' in c.lower()), 'wallet')
        
        df['timestamp'] = pd.to_datetime(df[d_col], utc=True).dt.tz_localize(None)
        df['date_only'] = df['timestamp'].dt.date
        df['usd_amount'] = pd.to_numeric(df[a_col]) / 1_000_000
        df['NODE_RAW'] = df[node_col]; df['LIC_RAW'] = df[lic_col]
        df['WALLET_RAW'] = df[wall_col] if wall_col in df.columns else "Unknown"
        df['NODE_ID'] = df['NODE_RAW'].apply(format_id); df['LIC_ID'] = df['LIC_RAW'].apply(format_id)
        
        return df, true_balance, None
    except Exception as e: return None, 0, str(e)

# --- 5. SIDEBAR ---
st.sidebar.title("🔐 ACCESS CONTROL")
with st.sidebar.expander("❓ TOKEN GUIDE"):
    st.markdown("1. Login to Unity site\n2. F12 > Network\n3. Refresh\n4. Find `allocations`\n5. Copy Bearer string.")
raw_input = st.sidebar.text_area("Paste Bearer Token:", height=100)
if st.sidebar.button("🔄 FORCE RE-SYNC"):
    st.cache_data.clear()
    st.rerun()

# --- 6. MAIN RENDER ---
st.markdown("<h1>█ UNITY_CORE <span style='color:#00f2ff;'>MASTER_TERMINAL_v6</span></h1>", unsafe_allow_html=True)

if raw_input:
    df, balance, err = deep_sync(raw_input)
    if df is not None:
        
        # --- PRE-CALCULATIONS ---
        now = datetime.now()
        today = now.date()
        yest = today - timedelta(days=1)
        s_days = today - timedelta(days=7)
        
        r_7d = df[df['date_only'] >= s_days]['usd_amount'].sum()
        y_total = df[df['date_only'] == yest]['usd_amount'].sum()
        avg_daily = r_7d / 7

        # --- KPI SECTION ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("TOTAL BALANCE", f"${balance:,.2f}")
        m2.metric("REWARDS (7D)", f"${r_7d:,.2f}")
        m3.metric("YESTERDAY", f"${y_total:,.4f}")
        m4.metric("EST. MONTHLY", f"${avg_daily * 30:,.2f}", delta=f"${avg_daily:.2f}/day")

        # --- STATUS & PERFORMANCE GRIDS ---
        st.markdown("---")
        g1, g2 = st.columns(2)
        
        with g1:
            st.subheader("// NODE_HEARTBEAT")
            unique_lics = sorted(df['LIC_RAW'].unique())
            last_payouts = df.groupby('LIC_RAW')['timestamp'].max().to_dict()
            html_hb = '<div class="status-grid">'
            for i, lic in enumerate(unique_lics, 1):
                hrs = (now - last_payouts.get(lic)).total_seconds() / 3600
                cls = "bg-green" if hrs <= 48 else "bg-yellow" if hrs <= 96 else "bg-red"
                html_hb += f'<div class="status-box {cls}" title="ID: {lic} &#10;Last: {int(hrs)}h ago">#{i}</div>'
            html_hb += '</div>'
            st.markdown(html_hb, unsafe_allow_html=True)
            st.caption("🟢 <48h | 🟡 <96h | 🔴 Offline")

        with g2:
            st.subheader("// BASELINE_EFFICIENCY_HEATMAP")
            lic_avgs = []
            for lic in unique_lics:
                sub = df[df['LIC_RAW'] == lic]
                days = max(1, (now - sub['timestamp'].min()).days)
                # Apply 0.015 - 5.0 Filter
                clean_sub = sub[(sub['usd_amount'] >= 0.015) & (sub['usd_amount'] <= 5.0)]
                lic_avgs.append({'lic': lic, 'avg': clean_sub['usd_amount'].sum() / days})
            
            s_df = pd.DataFrame(lic_avgs)
            mi, ma = s_df['avg'].min(), s_df['avg'].max()
            html_heat = '<div class="status-grid">'
            for i, row in s_df.iterrows():
                score = 1.0 if ma==mi else (row['avg'] - mi) / (ma - mi)
                hue = int(score * 9) * (120 / 9)
                style = f"background: hsla({hue}, 100%, 50%, 0.1); border: 1px solid hsl({hue}, 100%, 50%); color: hsl({hue}, 100%, 75%);"
                html_heat += f'<div class="status-box" style="{style}" title="ID: {format_id(row["lic"])} &#10;Baseline: ${row["avg"]:.4f}/d">#{i+1}</div>'
            html_heat += '</div>'
            st.markdown(html_heat, unsafe_allow_html=True)
            st.caption(f"Performance Gradient: ${mi:.3f} -> ${ma:.3f}/day")

        # --- VISUAL ANALYTICS ---
        st.markdown("---")
        st.subheader("// VISUAL_INTELLIGENCE_STREAM")
        c1, c2 = st.columns(2)
        with c1:
            daily_v = df.groupby('date_only')['usd_amount'].sum().reset_index()
            st.plotly_chart(apply_chart_style(px.area(daily_v, x='date_only', y='usd_amount', title="DAILY REWARD FLOW", color_discrete_sequence=['#00f2ff'])), use_container_width=True)
        with c2:
            tx_v = df.groupby('date_only').size().reset_index(name='count')
            st.plotly_chart(apply_chart_style(px.bar(tx_v, x='date_only', y='count', title="TRANSACTION VOLUME", color_discrete_sequence=['#7000ff'])), use_container_width=True)

        # --- NODE LOG ---
        st.markdown("---")
        st.subheader("// NODE_HARDWARE_LOG")
        node_stats = df.groupby('NODE_ID').agg({'LIC_RAW': 'nunique', 'usd_amount': 'sum'}).reset_index().rename(columns={'LIC_RAW': 'In Use', 'usd_amount': 'Total'})
        node_stats['Available'] = 200 - node_stats['In Use']
        node_7d = df[df['date_only'] >= s_days].groupby('NODE_ID')['usd_amount'].sum().reset_index().rename(columns={'usd_amount': '7D_Sum'})
        node_stats = pd.merge(node_stats, node_7d, on='NODE_ID', how='left').fillna(0)
        node_stats['Avg / Lic'] = node_stats['Total'] / node_stats['In Use']
        node_stats['Avg Daily (7D)'] = node_stats['7D_Sum'] / 7
        st.dataframe(node_stats.sort_values('Total', ascending=False).drop(columns=['7D_Sum']), column_config={"Total": st.column_config.NumberColumn(format="$ %.4f"), "Avg / Lic": st.column_config.NumberColumn(format="$ %.4f"), "Avg Daily (7D)": st.column_config.NumberColumn(format="$ %.4f")}, hide_index=True, use_container_width=True)

        # --- DRILLDOWN ---
        st.markdown("---")
        st.subheader("// LICENSE_DIAGNOSTICS")
        lic_map = {f"#{unique_lics.index(l)+1} - {format_id(l)}": l for l in unique_lics}
        sel = st.selectbox("Select Target License:", options=list(lic_map.keys()))
        lic_raw = lic_map[sel]
        l_df = df[df['LIC_RAW'] == lic_raw].sort_values('timestamp')
        
        st.markdown(f"<div class='drilldown-box'>### 🔍 CORE_DIAGNOSTICS: {sel}", unsafe_allow_html=True)
        d1, d2, d3 = st.columns(3)
        start = l_df['timestamp'].min(); days = max(1, (now - start).days)
        d1.markdown(f"**ACTIVE SINCE:**<br>{start.strftime('%Y-%m-%d')}<br>({days} Days)", unsafe_allow_html=True)
        d2.markdown(f"**DAILY AVG:** ${l_df['usd_amount'].sum()/days:,.4f}<br>**PEAK:** ${l_df['usd_amount'].max():,.4f}", unsafe_allow_html=True)
        d3.markdown(f"**NODE:** {format_id(l_df['NODE_RAW'].iloc[0])}<br>**WALLET:** {l_df['WALLET_RAW'].iloc[0]}", unsafe_allow_html=True)
        
        seen_dates = set(l_df['date_only'].unique())
        outages = [d.date() for d in pd.date_range(start.date(), today) if d.date() not in seen_dates]
        if outages: 
            st.warning(f"⚠️ {len(outages)} DAYS OFFLINE DETECTED")
            with st.expander("View Outage History"): st.write(", ".join([o.strftime('%b %d') for o in outages]))
        else: st.success("✅ 100% STABILITY RECORDED")
        st.markdown("</div>", unsafe_allow_html=True)

        # --- MATRIX (BOTTOM) ---
        st.markdown("---")
        st.subheader("// PERFORMANCE_MATRIX (7D)")
        d_range = [(today - timedelta(days=i)) for i in range(1, 8)]
        lic_tot = df.groupby('LIC_RAW')['usd_amount'].sum().rename('TOTAL_USD').reset_index()
        piv = df[df['date_only'].isin(d_range)].pivot_table(index='LIC_RAW', columns='date_only', values='usd_amount', aggfunc='sum').fillna(0)
        piv.columns = [d.strftime('%Y-%m-%d') for d in piv.columns]
        mat = pd.merge(lic_tot, piv, on='LIC_RAW', how='left').fillna(0).sort_values('TOTAL_USD', ascending=False)
        mat['LIC_RAW'] = mat['LIC_RAW'].apply(format_id)
        cnf = {"LIC_RAW": "ID", "TOTAL_USD": st.column_config.NumberColumn("TOTAL", format="$ %.4f")}
        for d in d_range: cnf[d.strftime('%Y-%m-%d')] = st.column_config.NumberColumn(d.strftime('%b %d'), format="$ %.4f")
        st.dataframe(mat, column_config=cnf, use_container_width=True, hide_index=True)

    else: st.error(f"📡 SYNC ERROR: {err}")
else: st.info("👈 SYSTEM LOCKED. Paste Bearer Token in sidebar to initialize.")
