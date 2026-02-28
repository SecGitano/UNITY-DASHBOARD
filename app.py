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

st.set_page_config(page_title="Unity Analytics // Hando Core", layout="wide", page_icon="📊")

# --- 2. HANDO MODERN SAAS UI THEME ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    h1, h2, h3 { color: #1e293b; font-weight: 700 !important; letter-spacing: -0.5px; }
    .stMarkdown { color: #64748b; }

    /* Sidebar Styling (Hando Navy) */
    [data-testid="stSidebar"] { background-color: #1e293b !important; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    [data-testid="stSidebar"] .stButton button { 
        background-color: #4f46e5 !important; border: none; color: white !important; border-radius: 8px;
    }

    /* KPI Metrics Card Styling */
    [data-testid="stMetric"] { 
        background: #ffffff; border: 1px solid #e2e8f0; 
        padding: 20px !important; border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    [data-testid="stMetricLabel"] { color: #64748b; font-weight: 500; font-size: 0.85rem; }
    [data-testid="stMetricValue"] { color: #1e293b; font-weight: 700; }

    /* Custom Card Container */
    .hando-card {
        background: white; border: 1px solid #e2e8f0; padding: 24px;
        border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }

    /* Status Grid */
    .status-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(45px, 1fr)); gap: 8px; margin: 15px 0; }
    .status-box { 
        padding: 10px 0; text-align: center; border-radius: 6px; 
        font-weight: 600; font-size: 0.75em; transition: 0.3s;
    }
    
    /* Hando Badge Colors */
    .bg-green { background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; }
    .bg-yellow { background: #fef9c3; color: #a16207; border: 1px solid #fef08a; }
    .bg-red { background: #fee2e2; color: #b91c1c; border: 1px solid #fecaca; }

    /* Table & Dataframe */
    .stDataFrame { border: 1px solid #e2e8f0; border-radius: 12px; }
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
        font_family="Inter", font_color="#64748b",
        title_font_size=18, title_font_color="#1e293b",
        xaxis=dict(showgrid=True, gridcolor='#f1f5f9'),
        yaxis=dict(showgrid=True, gridcolor='#f1f5f9'),
        margin=dict(t=40, b=0, l=0, r=0)
    )
    fig.update_traces(marker_line_width=0)
    return fig

# --- 4. DATA ENGINE ---
@st.cache_data(ttl=600, show_spinner=False)
def deep_sync(token):
    clean_token = token.strip().replace('Bearer ', '')
    headers = {"apikey": API_KEY, "authorization": f"Bearer {clean_token}", "content-type": "application/json"}
    try:
        r_bal = requests.post(API_URL_BAL, headers=headers, json={}, timeout=10)
        true_balance = parse_balance(r_bal.json()) / 1_000_000
        
        all_recs = []; skip = 0; batch = 1000
        sync_status = st.empty()
        while True:
            sync_status.info(f"Connecting to node registry... (Packet {skip})")
            r_his = requests.post(API_URL_HIS, headers=headers, json={"skip": skip, "take": batch}, timeout=15)
            if r_his.status_code != 200: break
            data = r_his.json()
            if not isinstance(data, list) or not data: break
            all_recs.extend(data)
            if len(data) < batch: break
            skip += batch
        sync_status.empty()
        
        if not all_recs: return None, true_balance, "History empty."
        
        df = pd.DataFrame(all_recs)
        df['timestamp'] = pd.to_datetime(df['created_at'], utc=True).dt.tz_localize(None)
        df['date_only'] = df['timestamp'].dt.date
        df['usd_amount'] = pd.to_numeric(df['amount']) / 1_000_000
        df['NODE_ID'] = df['node_id'].apply(format_id)
        df['LIC_RAW'] = df['license_id']
        
        return df, true_balance, None
    except Exception as e: return None, 0, str(e)

# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='color:white;'>Hando.</h2>", unsafe_allow_html=True)
    st.markdown("### ACCESS CONTROL")
    raw_input = st.text_area("Bearer Token", placeholder="Paste token here...", height=150)
    if st.button("REFRESH DATA", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    st.caption("v2.4.0 - Premium Analytics")

# --- 6. MAIN RENDER ---
st.title("Analytics Overview")
st.markdown("Welcome back! Here's what's happening with your nodes today.")

if raw_input:
    df, balance, err = deep_sync(raw_input)
    if df is not None:
        
        # Calculations
        now = datetime.now()
        today = now.date()
        yest = today - timedelta(days=1)
        s_days = today - timedelta(days=7)
        r_7d = df[df['date_only'] >= s_days]['usd_amount'].sum()
        y_total = df[df['date_only'] == yest]['usd_amount'].sum()
        avg_daily = r_7d / 7

        # --- KPI SECTION ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Wallet Balance", f"${balance:,.2f}")
        m2.metric("Revenue (7D)", f"${r_7d:,.2f}")
        m3.metric("Yesterday", f"${y_total:,.4f}")
        m4.metric("Est. Monthly", f"${avg_daily * 30:,.2f}")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- GRIDS ---
        g1, g2 = st.columns([1, 1])
        
        with g1:
            st.markdown('<div class="hando-card">', unsafe_allow_html=True)
            st.subheader("Node Heartbeat")
            unique_lics = sorted(df['LIC_RAW'].unique())
            last_payouts = df.groupby('LIC_RAW')['timestamp'].max().to_dict()
            html_hb = '<div class="status-grid">'
            for i, lic in enumerate(unique_lics, 1):
                hrs = (now - last_payouts.get(lic)).total_seconds() / 3600
                cls = "bg-green" if hrs <= 48 else "bg-yellow" if hrs <= 96 else "bg-red"
                html_hb += f'<div class="status-box {cls}">#{i}</div>'
            html_hb += '</div>'
            st.markdown(html_hb, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with g2:
            st.markdown('<div class="hando-card">', unsafe_allow_html=True)
            st.subheader("Performance Heatmap")
            lic_avgs = []
            for lic in unique_lics:
                sub = df[df['LIC_RAW'] == lic]
                days = max(1, (now - sub['timestamp'].min()).days)
                lic_avgs.append({'avg': sub['usd_amount'].sum() / days})
            s_df = pd.DataFrame(lic_avgs)
            mi, ma = s_df['avg'].min(), s_df['avg'].max()
            html_heat = '<div class="status-grid">'
            for i, row in s_df.iterrows():
                score = 1.0 if ma==mi else (row['avg'] - mi) / (ma - mi)
                # Hando-style Indigo Gradient
                alpha = 0.1 + (score * 0.9)
                html_heat += f'<div class="status-box" style="background: rgba(79, 70, 229, {alpha}); color: {"white" if alpha > 0.5 else "#4f46e5"}; border: 1px solid #4f46e5;">#{i+1}</div>'
            html_heat += '</div>'
            st.markdown(html_heat, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # --- CHARTS ---
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="hando-card">', unsafe_allow_html=True)
            daily_v = df.groupby('date_only')['usd_amount'].sum().reset_index()
            fig = px.area(daily_v, x='date_only', y='usd_amount', title="Revenue Stream", color_discrete_sequence=['#4f46e5'])
            st.plotly_chart(apply_chart_style(fig), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="hando-card">', unsafe_allow_html=True)
            tx_v = df.groupby('date_only').size().reset_index(name='count')
            fig = px.bar(tx_v, x='date_only', y='count', title="Activity Volume", color_discrete_sequence=['#94a3b8'])
            st.plotly_chart(apply_chart_style(fig), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # --- TABLES ---
        st.subheader("Node Performance Intelligence")
        node_stats = df.groupby('NODE_ID').agg({'LIC_RAW': 'nunique', 'usd_amount': 'sum'}).reset_index()
        node_stats.columns = ['Node ID', 'Licenses', 'Total Earned']
        
        st.dataframe(node_stats.sort_values('Total Earned', ascending=False), 
                     column_config={"Total Earned": st.column_config.NumberColumn(format="$ %.4f")}, 
                     hide_index=True, use_container_width=True)

        # --- DRILLDOWN ---
        st.markdown('<div class="hando-card" style="background:#f1f5f9; border:none;">', unsafe_allow_html=True)
        st.subheader("Detailed Diagnostics")
        lic_map = {f"Node License #{unique_lics.index(l)+1} ({format_id(l)})": l for l in unique_lics}
        sel = st.selectbox("Select specific license for deep-dive:", options=list(lic_map.keys()))
        lic_raw = lic_map[sel]
        l_df = df[df['LIC_RAW'] == lic_raw]
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Total Payouts", len(l_df))
        col_b.metric("Avg Daily", f"${l_df['usd_amount'].sum()/max(1,(now-l_df['timestamp'].min()).days):,.4f}")
        col_c.metric("Status", "STABLE" if len(l_df[l_df['date_only'] == yest]) > 0 else "INACTIVE", delta_color="normal")
        st.markdown('</div>', unsafe_allow_html=True)

    else: st.error(f"Sync failed: {err}")
else:
    st.info("System Standby. Please enter your Bearer Token in the sidebar to initialize analytics.")
