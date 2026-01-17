import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# --- SYSTEM CONFIG ---
API_URL_BAL = "https://api.unityedge.io/rest/v1/rpc/rewards_get_balance"
API_URL_HIS = "https://api.unityedge.io/rest/v1/rpc/rewards_get_allocations"
API_KEY = "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c"

st.set_page_config(page_title="UNITY_CORE // INTELLIGENCE", layout="wide")

# --- UI THEME ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono&display=swap');
    .stApp { background-color: #0d1117; font-family: 'JetBrains+Mono', monospace; }
    [data-testid="stMetric"] { background: #161b22; border: 1px solid #30363d; border-left: 5px solid #00f2ff; padding: 15px; }
    h1, h2, h3 { font-family: 'Orbitron', sans-serif; color: #f0f6fc; }
    .drilldown-box { background: #161b22; border: 1px solid #00f2ff; padding: 20px; border-radius: 8px; margin-top: 20px; }
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
@st.cache_data(ttl=300)
def sync_data(token):
    clean_token = token.strip().replace('Bearer ', '')
    headers = {"apikey": API_KEY, "authorization": f"Bearer {clean_token}", "content-type": "application/json"}
    try:
        r_bal = requests.post(API_URL_BAL, headers=headers, json={}, timeout=10)
        true_balance = parse_balance(r_bal.json()) / 1_000_000
        all_records = []; skip = 0; batch_size = 1000 
        while True:
            r_his = requests.post(API_URL_HIS, headers=headers, json={"skip": skip, "take": batch_size}, timeout=15)
            batch = r_his.json()
            if not isinstance(batch, list) or len(batch) == 0: break
            all_records.extend(batch)
            if len(batch) < batch_size: break
            skip += batch_size
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

# --- MAIN RENDER ---
st.markdown("<h1>█ UNITY_CORE <span style='color:#00f2ff;'>INTELLIGENCE_CENTER</span></h1>", unsafe_allow_html=True)

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

        # --- NODE LOG ---
        st.subheader("// NODE_PERFORMANCE_LOG")
        node_stats = df.groupby('NODE_ID').agg({'LIC_RAW': 'nunique','usd_amount': 'sum'}).reset_index().rename(columns={'LIC_RAW': 'In Use', 'usd_amount': 'Total'})
        node_stats['Available'] = 200 - node_stats['In Use']
        node_stats['Avg / Lic'] = node_stats['Total'] / node_stats['In Use']
        st.dataframe(node_stats.sort_values('Total', ascending=False), hide_index=True, use_container_width=True)

        st.markdown("---")

        # --- LICENSE MATRIX WITH SELECTION ---
        st.subheader("// LICENSE_INTELLIGENCE_MATRIX (7D)")
        st.caption("Click a row to inspect detailed license diagnostics.")
        
        date_list = [(today - timedelta(days=i)) for i in range(1, 8)]
        lic_tot = df.groupby('LIC_RAW')['usd_amount'].sum().rename('TOTAL_USD').reset_index()
        p_7d = df[df['date_only'].isin(date_list)].pivot_table(index='LIC_RAW', columns='date_only', values='usd_amount', aggfunc='sum').fillna(0)
        p_7d.columns = [d.strftime('%Y-%m-%d') for d in p_7d.columns]
        
        matrix = pd.merge(lic_tot, p_7d, on='LIC_RAW', how='left').fillna(0).sort_values('TOTAL_USD', ascending=False)
        matrix_display = matrix.copy()
        matrix_display['LIC_RAW'] = matrix_display['LIC_RAW'].apply(format_id)
        
        # New Selection Logic (Available in Streamlit 1.35+)
        selection = st.dataframe(
            matrix_display, 
            on_select="rerun", 
            selection_mode="single_row", 
            use_container_width=True,
            hide_index=True,
            column_config={"LIC_RAW": "LICENSE_ID", "TOTAL_USD": st.column_config.NumberColumn("TOTAL", format="$ %.4f")}
        )

        # --- DRILL-DOWN PANEL ---
        if selection and len(selection.selection.rows) > 0:
            selected_idx = selection.selection.rows[0]
            selected_lic_raw = matrix.iloc[selected_idx]['LIC_RAW']
            lic_df = df[df['LIC_RAW'] == selected_lic_raw].sort_values('timestamp')
            
            st.markdown(f"<div class='drilldown-box'>", unsafe_allow_html=True)
            st.subheader(f"🔍 DIAGNOSTICS: {format_id(selected_lic_raw)}")
            
            d1, d2, d3 = st.columns(3)
            
            # 1. Timeline Info
            first_seen = lic_df['timestamp'].min()
            days_active = (datetime.now() - first_seen).days
            d1.markdown(f"**ONLINE SINCE:**<br>{first_seen.strftime('%Y-%m-%d')}<br>({days_active} days ago)", unsafe_allow_html=True)
            
            # 2. Financial Info
            avg_daily = lic_df['usd_amount'].sum() / (days_active if days_active > 0 else 1)
            highest = lic_df['usd_amount'].max()
            d2.markdown(f"**AVG DAILY REVENUE:**<br>${avg_daily:,.4f}<br>**PEAK REWARD:** ${highest:,.4f}", unsafe_allow_html=True)
            
            # 3. Association Info
            wallet = lic_df['WALLET_RAW'].iloc[0]
            node = format_id(lic_df['NODE_RAW'].iloc[0])
            d3.markdown(f"**WALLET:** {wallet}<br>**NODE:** {node}", unsafe_allow_html=True)
            
            # 4. Outage Detection (Simple logic: missed days)
            st.write("---")
            all_dates = pd.date_range(start=first_seen.date(), end=datetime.now().date())
            seen_dates = lic_df['date_only'].unique()
            outages = [d for d in all_dates.date if d not in seen_dates]
            
            if outages:
                st.warning(f"⚠️ ESTIMATED OUTAGES: {len(outages)} days detected.")
                with st.expander("View Outage Dates"):
                    st.write(", ".join([d.strftime('%b %d') for d in outages]))
            else:
                st.success("✅ NO SIGNIFICANT OUTAGES DETECTED")
            
            st.markdown("</div>", unsafe_allow_html=True)
            
    else: st.error(f"📡 SYNC FAILED: {err}")
else: st.info("👈 Authentication Required. Paste Bearer Token in sidebar.")
