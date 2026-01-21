import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- TRY IMPORTING WALLET CONNECT ---
try:
    from wallet_connect import wallet_connect
    WALLET_LIB_AVAILABLE = True
except ImportError:
    WALLET_LIB_AVAILABLE = False

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
    .wallet-box { border: 1px solid #7000ff; background: rgba(112, 0, 255, 0.1); padding: 10px; border-radius: 5px; margin-bottom: 20px; text-align: center; }
    
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
    .status-blue { background: rgba(0, 100, 255, 0.2); border: 1px solid #00f2ff; color: #00f2ff; box-shadow: 0 0 15px rgba(0, 242, 255, 0.3); } /* YOUR NODES */

    </style>
    """, unsafe_allow_html=True)

# --- UTILITIES & PARSERS ---
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

# --- SIDEBAR: AUTH & WALLET ---
st.sidebar.title("🔐 ACCESS CONTROL")
with st.sidebar.expander("❓ HOW TO GET TOKEN"):
    st.markdown("1. Login to Unity site.\n2. F12 > Network.\n3. Refresh page.\n4. Find `Reward get allocations`.\n5. Copy Authorization Bearer string.")
raw_input = st.sidebar.text_area("Paste Bearer Token:", height=100)

st.sidebar.markdown("---")
st.sidebar.subheader("🔗 WEB3 CONNECTION")

user_wallet = None

if WALLET_LIB_AVAILABLE:
    # Use the library button
    wallet_btn_key = "wallet_connect_btn"
    connect_btn = wallet_connect(label="Connect Wallet", key=wallet_btn_key)
    if connect_btn:
        user_wallet = str(connect_btn).lower()
        st.sidebar.success(f"✅ CONNECTED: {user_wallet[:6]}...{user_wallet[-4:]}")
else:
    # Fallback if library missing
    st.sidebar.warning("⚠️ 'streamlit-wallet-connect' not detected.")
    user_wallet_input = st.sidebar.text_input("Manual Wallet Address (Optional):")
    if user_wallet_input:
        user_wallet = user_wallet_input.strip().lower()

if st.sidebar.button("🔄 FORCE REFRESH"):
    st.cache_data.clear()
    st.rerun()

# --- MAIN APP ---
st.markdown("<h1>█ UNITY_CORE <span style='color:#00f2ff;'>VAL's MASTER TERMINAL v3.0</span></h1>", unsafe_allow_html=True)

if raw_input:
    df, balance, err = sync_data(raw_input)
    if df is not None:
        
        # --- 1. IDENTIFY USER DATA ---
        my_df = pd.DataFrame()
        is_owner = False
        
        if user_wallet:
            # Filter data for connected wallet
            # Note: We convert column to lower for safe comparison
            my_df = df[df['WALLET_RAW'].astype(str).str.lower() == user_wallet]
            if not my_df.empty:
                is_owner = True
                st.markdown(f"<div class='wallet-box'>⚡ RECOGNIZED OWNER: <span style='color:#00f2ff'>{user_wallet}</span> | NODES: {my_df['LIC_RAW'].nunique()}</div>", unsafe_allow_html=True)
            else:
                st.warning(f"⚠️ Wallet connected ({format_id(user_wallet)}), but no matching records found in this dataset.")

        # --- 2. HEADER METRICS (Global vs Personal) ---
        today = datetime.now().date()
        s_days = today - timedelta(days=7)
        
        # Calculate Global Stats
        r_7d = df[df['date_only'] >= s_days]['usd_amount'].sum()
        y_total = df[df['date_only'] == (today - timedelta(days=1))]['usd_amount'].sum()
        
        # Calculate Personal Stats (if wallet connected)
        my_r7d = my_df[my_df['date_only'] >= s_days]['usd_amount'].sum() if is_owner else 0
        my_proj = (my_r7d / 7) * 30 if is_owner else 0
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("TOTAL BALANCE (API)", f"${balance:,.2f}")
        m2.metric("GLOBAL REWARDS (7D)", f"${r_7d:,.2f}")
        
        if is_owner:
            m3.metric("💸 MY REWARDS (7D)", f"${my_r7d:,.2f}", delta="Wallet Filtered")
            m4.metric("📅 MY EST. MONTHLY", f"${my_proj:,.2f}", delta=f"${(my_r7d/7):.2f}/day")
        else:
            m3.metric("YESTERDAY (GLOBAL)", f"${y_total:,.4f}")
            avg_7d = r_7d / 7
            m4.metric("EST. MONTHLY (GLOBAL)", f"${avg_7d * 30:,.2f}")

        # --- 3. STATUS GRID (TRAFFIC LIGHT) ---
        st.markdown("---")
        st.subheader("// SYSTEM_STATUS_GRID (HEARTBEAT)")
        
        # If owner, we prioritize showing THEIR nodes first or highlighting them
        unique_lics = sorted(df['LIC_RAW'].unique())
        my_lics = set(my_df['LIC_RAW'].unique()) if is_owner else set()
        
        last_seen_map = df.groupby('LIC_RAW')['timestamp'].max().to_dict()
        now = datetime.now()
        
        c_green, c_yellow, c_red, c_blue = 0, 0, 0, 0
        
        html_grid = '<div class="status-grid">'
        for i, lic in enumerate(unique_lics, 1):
            last_ts = last_seen_map.get(lic)
            hours_since = (now - last_ts).total_seconds() / 3600
            
            # Determine Color
            is_mine = lic in my_lics
            
            if is_mine:
                # Special Blue Pulse for User Nodes
                status_class = "status-blue" 
                c_blue += 1
            elif hours_since <= 48:
                status_class = "status-green"
                c_green += 1
            elif 48 < hours_since <= 96:
                status_class = "status-yellow"
                c_yellow += 1
            else:
                status_class = "status-red"
                c_red += 1
                
            tooltip = f"ID: {lic} &#10;Last Reward: {int(hours_since)}h ago {'(YOURS)' if is_mine else ''}"
            html_grid += f'<div class="status-box {status_class}" title="{tooltip}">#{i}</div>'
        html_grid += '</div>'
        
        st.markdown(html_grid, unsafe_allow_html=True)
        
        legend_text = f"🟢 ONLINE (<48h): {c_green} | 🟡 WARNING (48-96h): {c_yellow} | 🔴 OFFLINE (>96h): {c_red}"
        if is_owner:
            legend_text = f"🔵 YOUR NODES: {c_blue} | " + legend_text
        st.caption(legend_text)

        # --- 4. CHARTS (Switchable) ---
        st.markdown("---")
        view_mode = "Global"
        if is_owner:
            c_label, c_toggle = st.columns([8, 2])
            with c_label: st.subheader(f"// VISUAL_ANALYTICS")
            with c_toggle: view_mode = st.radio("View Mode", ["Global", "My Farm"], horizontal=True)
        else:
            st.subheader("// VISUAL_ANALYTICS")

        # Determine which DF to use for charts
        chart_df = my_df if view_mode == "My Farm" and is_owner else df
        
        if not chart_df.empty:
            c1, c2 = st.columns(2)
            with c1:
                daily_acc = chart_df.groupby('date_only')['usd_amount'].sum().reset_index()
                daily_acc['MA7'] = daily_acc['usd_amount'].rolling(window=7).mean()
                fig1 = px.area(daily_acc, x='date_only', y='usd_amount', title=f"{view_mode.upper()} REWARD FLOW", template="plotly_dark")
                fig1.add_trace(go.Scatter(x=daily_acc['date_only'], y=daily_acc['MA7'], mode='lines', name='7-Day Trend', line=dict(color='white', dash='dot')))
                fig1.update_traces(line_color='#00f2ff', fillcolor='rgba(0, 242, 255, 0.1)', selector=dict(type='area'))
                st.plotly_chart(fig1, use_container_width=True)
            with c2:
                node_rew = chart_df.groupby('NODE_ID')['usd_amount'].sum().sort_values(ascending=False).reset_index()
                fig2 = px.bar(node_rew, x='NODE_ID', y='usd_amount', title=f"{view_mode.upper()} BY NODE", template="plotly_dark", color='usd_amount', color_continuous_scale='Blues')
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No data available for 'My Farm' view.")

        # --- 5. DRILLDOWN ---
        st.markdown("---")
        st.subheader("// LICENSE_INTELLIGENCE_DRILLDOWN")
        
        # Filter Dropdown based on view mode
        target_lics = sorted(chart_df['LIC_RAW'].unique())
        lic_display_map = {f"#{unique_lics.index(l)+1} - {format_id(l)}": l for l in target_lics}
        
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

        # --- 6. MATRIX ---
        st.markdown("---")
        st.subheader(f"// {view_mode.upper()} MATRIX (7D)")
        date_list = [(today - timedelta(days=i)) for i in range(1, 8)]
        lic_tot = chart_df.groupby('LIC_RAW')['usd_amount'].sum().rename('TOTAL_USD').reset_index()
        p_7d = chart_df[chart_df['date_only'].isin(date_list)].pivot_table(index='LIC_RAW', columns='date_only', values='usd_amount', aggfunc='sum').fillna(0)
        p_7d.columns = [d.strftime('%Y-%m-%d') for d in p_7d.columns]
        matrix = pd.merge(lic_tot, p_7d, on='LIC_RAW', how='left').fillna(0).sort_values('TOTAL_USD', ascending=False)
        matrix['LIC_RAW'] = matrix['LIC_RAW'].apply(format_id)
        conf = {"LIC_RAW": "LICENSE_ID", "TOTAL_USD": st.column_config.NumberColumn("TOTAL", format="$ %.4f")}
        for d in date_list: ds = d.strftime('%Y-%m-%d'); conf[ds] = st.column_config.NumberColumn(d.strftime('%b %d'), format="$ %.4f")
        st.dataframe(matrix, column_config=conf, use_container_width=True, hide_index=True)

    else: st.error(f"📡 SYNC FAILED: {err}")
else: st.info("👈 Authentication Required. Paste Bearer Token in sidebar.")
