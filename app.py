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

st.set_page_config(page_title="UNITY_CORE // VAL's MASTER TERMINAL", layout="wide", page_icon="💠")

# --- UI THEME ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono&display=swap');
    .stApp { background-color: #0d1117; font-family: 'JetBrains+Mono', monospace; }
    
    /* Metrics */
    [data-testid="stMetric"] { background: #161b22; border: 1px solid #30363d; border-left: 5px solid #00f2ff; padding: 15px; box-shadow: 0 0 10px rgba(0, 242, 255, 0.1); }
    [data-testid="stMetricLabel"] { color: #8b949e; font-size: 0.8rem; }
    [data-testid="stMetricValue"] { color: #f0f6fc; font-family: 'Orbitron', sans-serif; font-size: 1.8rem; }
    
    /* Headers */
    h1, h2, h3 { font-family: 'Orbitron', sans-serif; color: #f0f6fc; text-transform: uppercase; letter-spacing: 2px; }
    
    /* Custom Boxes */
    .drilldown-box { background: #11151c; border: 1px solid #00f2ff; padding: 25px; border-radius: 5px; margin: 20px 0; }
    
    /* STATUS GRID CSS */
    .status-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 10px; margin-top: 20px; margin-bottom: 20px; }
    .status-box { 
        padding: 15px; text-align: center; border-radius: 4px; 
        font-family: 'Orbitron', sans-serif; font-weight: bold; font-size: 0.9em; 
        cursor: help; transition: all 0.2s; position: relative;
    }
    .status-box:hover { transform: scale(1.1); z-index: 10; box-shadow: 0 0 15px rgba(255,255,255,0.2); }
    
    /* COLORS */
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
    """Helper to enforce deep dark mode on charts"""
    fig.update_layout(
        paper_bgcolor='#0d1117', # Matches App Background
        plot_bgcolor='#0d1117',
        font_family="JetBrains Mono",
        font_color="#8b949e",
        title_font_family="Orbitron",
        title_font_color="#f0f6fc",
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
    except: return None, 0, "Failed to fetch balance."

    try:
        all_records = []; skip = 0; batch_size = 1000 
        placeholder = st.empty()
        while True:
            placeholder.text(f"⏳ DATA LINK ESTABLISHED... DOWNLOADING PACKET {skip}...")
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
        wall_col = next((c for c in df.columns if 'wallet' in c.lower() or 'address' in c.lower()), 'wallet')
        
        df['timestamp'] = pd.to_datetime(df[d_col], utc=True).dt.tz_localize(None)
        df['date_only'] = df['timestamp'].dt.date
        df['usd_amount'] = pd.to_numeric(df[a_col]) / 1_000_000
        df['NODE_RAW'] = df[node_col]
        df['LIC_RAW'] = df[lic_col]
        df['WALLET_RAW'] = df[wall_col] if wall_col in df.columns else "Unknown"
        df['NODE_ID'] = df['NODE_RAW'].apply(format_id)
        df['LIC_ID'] = df['LIC_RAW'].apply(format_id)
        
        return df, true_balance, None
    except Exception as e: return None, 0, str(e)

# --- SIDEBAR ---
st.sidebar.title("🔐 ACCESS CONTROL")
with st.sidebar.expander("❓ HOW TO GET TOKEN"):
    st.markdown("1. Login to Unity site.\n2. F12 > Network.\n3. Refresh page.\n4. Find `Reward get allocations`.\n5. Copy Authorization Bearer string.")
raw_input = st.sidebar.text_area("Paste Bearer Token:", height=100)

if st.sidebar.button("🔄 FORCE REFRESH"):
    st.cache_data.clear()
    st.rerun()

# --- MAIN APP ---
st.markdown("<h1>█ UNITY_CORE <span style='color:#00f2ff;'>VAL's MASTER TERMINAL v4.2</span></h1>", unsafe_allow_html=True)

if raw_input:
    df, balance, err = sync_data(raw_input)
    if df is not None:
        
        # --- 1. HEADER METRICS ---
        today = datetime.now().date()
        s_days = today - timedelta(days=7)
        
        r_7d = df[df['date_only'] >= s_days]['usd_amount'].sum()
        y_total = df[df['date_only'] == (today - timedelta(days=1))]['usd_amount'].sum()
        avg_7d = r_7d / 7
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("TOTAL BALANCE", f"${balance:,.2f}")
        m2.metric("REWARDS (7D)", f"${r_7d:,.2f}")
        m3.metric("YESTERDAY", f"${y_total:,.4f}")
        m4.metric("EST. MONTHLY", f"${avg_7d * 30:,.2f}", delta=f"${avg_7d:.2f}/day")

        # --- 2. STATUS GRID (TRAFFIC LIGHT) ---
        st.markdown("---")
        st.subheader("// SYSTEM_STATUS_GRID (HEARTBEAT)")
        
        unique_lics = sorted(df['LIC_RAW'].unique())
        last_seen_map = df.groupby('LIC_RAW')['timestamp'].max().to_dict()
        now = datetime.now()
        
        c_green, c_yellow, c_red = 0, 0, 0
        
        html_grid = '<div class="status-grid">'
        for i, lic in enumerate(unique_lics, 1):
            last_ts = last_seen_map.get(lic)
            hours_since = (now - last_ts).total_seconds() / 3600
            
            if hours_since <= 48:
                status_class = "status-green"
                c_green += 1
            elif 48 < hours_since <= 96:
                status_class = "status-yellow"
                c_yellow += 1
            else:
                status_class = "status-red"
                c_red += 1
                
            tooltip = f"ID: {lic} &#10;Last Reward: {int(hours_since)}h ago"
            html_grid += f'<div class="status-box {status_class}" title="{tooltip}">#{i}</div>'
        html_grid += '</div>'
        
        st.markdown(html_grid, unsafe_allow_html=True)
        st.caption(f"🟢 ONLINE (<48h): {c_green} | 🟡 WARNING (48-96h): {c_yellow} | 🔴 OFFLINE (>96h): {c_red}")

        # --- 3. CHARTS (DARK MODE) ---
        st.markdown("---")
        st.subheader("// VISUAL_ANALYTICS")
        
        c1, c2, c3 = st.columns(3)
        
        # Chart 1: Total Volume (Area + Points)
        with c1:
            daily_acc = df.groupby('date_only')['usd_amount'].sum().reset_index()
            daily_acc['MA7'] = daily_acc['usd_amount'].rolling(window=7, min_periods=1).mean()
            
            fig1 = px.area(daily_acc, x='date_only', y='usd_amount', title="TOTAL DAILY VOLUME")
            fig1.add_trace(go.Scatter(x=daily_acc['date_only'], y=daily_acc['MA7'], mode='lines', name='7-Day Trend', line=dict(color='white', dash='dot')))
            fig1.update_traces(line_color='#00f2ff', fillcolor='rgba(0, 242, 255, 0.1)')
            fig1 = apply_dark_theme(fig1)
            st.plotly_chart(fig1, use_container_width=True)
            
        # Chart 2: Node Distribution (Bar)
        with c2:
            node_rew = df.groupby('NODE_ID')['usd_amount'].sum().sort_values(ascending=False).reset_index()
            fig2 = px.bar(node_rew, x='NODE_ID', y='usd_amount', title="TOTAL BY NODE", color='usd_amount', color_continuous_scale='Blues')
            fig2 = apply_dark_theme(fig2)
            st.plotly_chart(fig2, use_container_width=True)

        # Chart 3: Refined Average (Area + Points + Trend) - EXCL > $5
        with c3:
            refined_df = df[df['usd_amount'] <= 5.0]
            if not refined_df.empty:
                daily_avg = refined_df.groupby('date_only')['usd_amount'].mean().reset_index()
                # Rolling 7-day avg for the trend line
                daily_avg['MA7'] = daily_avg['usd_amount'].rolling(window=7, min_periods=1).mean()
                
                fig3 = px.area(daily_avg, x='date_only', y='usd_amount', title="BASELINE AVG (EXCL. >$5)")
                
                # Add Trend Line
                fig3.add_trace(go.Scatter(
                    x=daily_avg['date_only'], y=daily_avg['MA7'], 
                    mode='lines', name='7-Day Trend', 
                    line=dict(color='white', dash='dot')
                ))
                
                # Style the Area (Neon Purple) and enable points
                fig3.update_traces(
                    line_color='#d000ff', 
                    fillcolor='rgba(208, 0, 255, 0.1)', 
                    mode='lines+markers', # Adds points
                    marker=dict(size=4),
                    selector=dict(type='area')
                )
                
                fig3 = apply_dark_theme(fig3)
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No data found under $5.00 threshold.")

        # --- 4. DRILLDOWN ---
        st.markdown("---")
        st.subheader("// LICENSE_INTELLIGENCE_DRILLDOWN")
        
        lic_display_map = {f"#{unique_lics.index(l)+1} - {format_id(l)}": l for l in unique_lics}
        
        if lic_display_map:
            selected_display = st.selectbox("Inspect License Diagnostics:", options=list(lic_display_map.keys()))
            selected_lic_raw = lic_display_map[selected_display]
            lic_df = df[df['LIC_RAW'] == selected_lic_raw].sort_values('timestamp')
            
            st.markdown(f"<div class='drilldown-box'>### 🔍 DIAGNOSTICS: {selected_display}", unsafe_allow_html=True)
            d1, d2, d3 = st.columns(3)
            first_seen = lic_df['timestamp'].min(); days_act = (datetime.now() - first_seen).days
            d1.markdown(f"**ONLINE SINCE:**<br>{first_seen.strftime('%Y-%m-%d')}<br>({days_act} days active)", unsafe_allow_html=True)
            avg_d = lic_df['usd_amount'].sum() / (days_act if days_act > 0 else 1)
            d2.markdown(f"**AVG DAILY:** ${avg_d:,.4f}<br>**PEAK REWARD:** ${lic_df['usd_amount'].max():,.4f}", unsafe_allow_html=True)
            d3.markdown(f"**NODE ID:** {format_id(lic_df['NODE_RAW'].iloc[0])}<br>**WALLET:** {lic_df['WALLET_RAW'].iloc[0]}", unsafe_allow_html=True)
            
            all_dates = pd.date_range(start=first_seen.date(), end=today)
            seen_dates = set(lic_df['date_only'].unique())
            outages = [d.date() for d in all_dates if d.date() not in seen_dates]
            if outages: st.warning(f"⚠️ OUTAGE ALERT: {len(outages)} days with zero rewards."); st.write(", ".join([d.strftime('%b %d') for d in outages]))
            else: st.success("✅ LICENSE STABILITY: 100%")
            st.markdown("</div>", unsafe_allow_html=True)

        # --- 5. MATRIX ---
        st.markdown("---")
        st.subheader("// PERFORMANCE MATRIX (7D)")
        date_list = [(today - timedelta(days=i)) for i in range(1, 8)]
        lic_tot = df.groupby('LIC_RAW')['usd_amount'].sum().rename('TOTAL_USD').reset_index()
        p_7d = df[df['date_only'].isin(date_list)].pivot_table(index='LIC_RAW', columns='date_only', values='usd_amount', aggfunc='sum').fillna(0)
        p_7d.columns = [d.strftime('%Y-%m-%d') for d in p_7d.columns]
        matrix = pd.merge(lic_tot, p_7d, on='LIC_RAW', how='left').fillna(0).sort_values('TOTAL_USD', ascending=False)
        matrix['LIC_RAW'] = matrix['LIC_RAW'].apply(format_id)
        conf = {"LIC_RAW": "LICENSE_ID", "TOTAL_USD": st.column_config.NumberColumn("TOTAL", format="$ %.4f")}
        for d in date_list: ds = d.strftime('%Y-%m-%d'); conf[ds] = st.column_config.NumberColumn(d.strftime('%b %d'), format="$ %.4f")
        st.dataframe(matrix, column_config=conf, use_container_width=True, hide_index=True)

    else: st.error(f"📡 SYNC FAILED: {err}")
else: st.info("👈 Authentication Required. Paste Bearer Token in sidebar.")
