import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import datetime, timedelta

# --- 1. SYSTEM CONFIGURATION ---
API_URL_BAL = "https://api.unityedge.io/rest/v1/rpc/rewards_get_balance"
API_URL_HIS = "https://api.unityedge.io/rest/v1/rpc/rewards_get_allocations"
API_KEY = "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c"

st.set_page_config(page_title="Unity Analytics // Hando Core", layout="wide", page_icon="📊")

# --- 2. HANDO MODERN UI THEME ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .stApp { background-color: #f8fafc; font-family: 'Inter', sans-serif; }
    h1, h2, h3 { color: #1e293b; font-weight: 700 !important; letter-spacing: -0.5px; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #1e293b !important; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    [data-testid="stSidebar"] .stButton button { 
        background-color: #4f46e5 !important; border: none; color: white !important; border-radius: 8px;
    }

    /* KPI Metrics */
    [data-testid="stMetric"] { 
        background: #ffffff; border: 1px solid #e2e8f0; 
        padding: 20px !important; border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    [data-testid="stMetricLabel"] { color: #64748b; font-weight: 500; }
    [data-testid="stMetricValue"] { color: #1e293b; font-weight: 700; }

    /* Cards */
    .hando-card {
        background: white; border: 1px solid #e2e8f0; padding: 24px;
        border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }

    /* Status Grid */
    .status-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(45px, 1fr)); gap: 8px; margin: 15px 0; }
    .status-box { padding: 10px 0; text-align: center; border-radius: 6px; font-weight: 600; font-size: 0.75em; }
    
    .bg-green { background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; }
    .bg-yellow { background: #fef9c3; color: #a16207; border: 1px solid #fef08a; }
    .bg-red { background: #fee2e2; color: #b91c1c; border: 1px solid #fecaca; }
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
        xaxis=dict(showgrid=True, gridcolor='#f1f5f9'),
        yaxis=dict(showgrid=True, gridcolor='#f1f5f9'),
        margin=dict(t=40, b=0, l=0, r=0)
    )
    return fig

# --- 4. DATA ENGINE (FIXED: Restored your original column-finding logic) ---
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
            sync_status.info(f"⏳ Syncing node data packet {skip}...")
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
        
        # --- DYNAMIC COLUMN FINDER (Restored from your working code) ---
        d_col = next((c for c in df.columns if 'time' in c or 'created' in c), 'created_at')
        a_col = next((c for c in df.columns if 'amount' in c or 'reward' in c), 'amount')
        node_col = next((c for c in df.columns if 'node' in c.lower()), 'node_id')
        lic_col = next((c for c in df.columns if 'license' in c.lower()), 'license_id')
        
        # Apply logic
        df['timestamp'] = pd.to_datetime(df[d_col], utc=True).dt.tz_localize(None)
        df['date_only'] = df['timestamp'].dt.date
        df['usd_amount'] = pd.to_numeric(df[a_col]) / 1_000_000
        df['NODE_RAW'] = df[node_col]
        df['LIC_RAW'] = df[lic_col]
        df['NODE_ID'] = df['NODE_RAW'].apply(format_id)
        
        return df, true_balance, None
    except Exception as e: return None, 0, str(e)

# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown("<h2 style='color:white;'>Hando.</h2>", unsafe_allow_html=True)
    raw_input = st.text_area("Bearer Token", placeholder="Paste token here...", height=150)
    if st.button("REFRESH DATA", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- 6. MAIN RENDER ---
st.title("Analytics Overview")

if raw_input:
    df, balance, err = deep_sync(raw_input)
    if df is not None:
        # Pre-calcs
        now = datetime.now()
        today = now.date()
        yest = today - timedelta(days=1)
        s_days = today - timedelta(days=7)
        r_7d = df[df['date_only'] >= s_days]['usd_amount'].sum()
        y_total = df[df['date_only'] == yest]['usd_amount'].sum()
        avg_daily = r_7d / 7

        # KPIs
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Wallet Balance", f"${balance:,.2f}")
        m2.metric("Revenue (7D)", f"${r_7d:,.2f}")
        m3.metric("Yesterday", f"${y_total:,.4f}")
        m4.metric("Est. Monthly", f"${avg_daily * 30:,.2f}")

        st.markdown("<br>", unsafe_allow_html=True)

        # Grids
        g1, g2 = st.columns(2)
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
            st.subheader("Revenue Stream")
            daily_v = df.groupby('date_only')['usd_amount'].sum().reset_index()
            fig = px.area(daily_v, x='date_only', y='usd_amount', color_discrete_sequence=['#4f46e5'])
            st.plotly_chart(apply_chart_style(fig), use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # Performance Table
        st.subheader("Node Intelligence")
        node_stats = df.groupby('NODE_ID').agg({'LIC_RAW': 'nunique', 'usd_amount': 'sum'}).reset_index()
        node_stats.columns = ['Node ID', 'Licenses', 'Total Earned']
        st.dataframe(node_stats.sort_values('Total Earned', ascending=False), 
                     column_config={"Total Earned": st.column_config.NumberColumn(format="$ %.4f")}, 
                     hide_index=True, use_container_width=True)

    else: st.error(f"Sync failed: {err}")
else:
    st.info("System Standby. Please enter your Bearer Token in the sidebar.")
