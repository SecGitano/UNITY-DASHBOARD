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
    .stDataFrame { border: 1px solid #30363d; border-radius: 4px; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.title("🔐 ACCESS CONTROL")
raw_input = st.sidebar.text_area("Paste Bearer Token:", height=100)

def sync_data(token):
    clean_token = token.strip().replace('Bearer ', '')
    headers = {"apikey": API_KEY, "authorization": f"Bearer {clean_token}", "content-type": "application/json"}
    
    try:
        # 1. Fetch Balance
        r_bal = requests.post(API_URL_BAL, headers=headers, json={}, timeout=10)
        bal_json = r_bal.json()
        true_balance = float(next(iter(bal_json[0].values()) if isinstance(bal_json, list) else bal_json.values())) / 1_000_000

        # 2. Fetch History
        r_his = requests.post(API_URL_HIS, headers=headers, json={"skip": None, "take": None}, timeout=10)
        df = pd.DataFrame(r_his.json())
        
        # --- COLUMN DETECTION ---
        # We look for identifiers for licenses and nodes
        lic_col = next((c for c in df.columns if 'license' in c.lower()), 'license_id')
        node_col = next((c for c in df.columns if 'node' in c.lower()), 'node_id')
        d_col = next((c for c in df.columns if 'time' in c or 'created' in c), 'created_at')
        a_col = next((c for c in df.columns if 'amount' in c or 'reward' in c), 'amount')

        df['timestamp'] = pd.to_datetime(df[d_col], utc=True).dt.tz_localize(None)
        df['date'] = df['timestamp'].dt.date
        df['usd_amount'] = pd.to_numeric(df[a_col]) / 1_000_000
        
        # Rename for consistency in logic
        df = df.rename(columns={lic_col: 'LIC_ID', node_col: 'NODE_ID'})
        
        return df, true_balance, None
    except Exception as e:
        return None, 0, str(e)

# --- MAIN INTERFACE ---
st.markdown("<h1>█ UNITY_CORE <span style='color:#00f2ff;'>ADVANCED_ANALYTICS</span></h1>", unsafe_allow_html=True)

if raw_input:
    df, balance, err = sync_data(raw_input)
    
    if df is not None:
        # --- CALCULATIONS ---
        total_nodes = df['NODE_ID'].nunique()
        total_lics = df['LIC_ID'].nunique()
        history_total = df['usd_amount'].sum()
        
        # 1. TOP METRICS
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("ACCOUNT BALANCE", f"${balance:,.2f}")
        m2.metric("UNIQUE NODES", total_nodes)
        m3.metric("ACTIVE LICENSES", total_lics)
        m4.metric("AVG LIC / NODE", round(total_lics / total_nodes, 1) if total_nodes > 0 else 0)

        st.markdown("---")

        # 2. NODE BREAKDOWN SECTION
        st.subheader("// NODE_REWARD_DISTRIBUTION")
        c1, c2 = st.columns([2, 1])
        
        # Group by Node
        node_stats = df.groupby('NODE_ID').agg({
            'LIC_ID': 'nunique',
            'usd_amount': 'sum'
        }).reset_index().rename(columns={'LIC_ID': 'Licenses', 'usd_amount': 'Total Rewards ($)'})

        with c1:
            fig_node = px.bar(node_stats, x='NODE_ID', y='Total Rewards ($)', 
                             color='Total Rewards ($)', template="plotly_dark",
                             color_continuous_scale='GnBu')
            fig_node.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_node, use_container_width=True)
            
        with c2:
            st.write("#### Node Summary")
            st.dataframe(node_stats, hide_index=True, use_container_width=True)

        st.markdown("---")

        # 3. 7-DAY LICENSE PERFORMANCE MATRIX
        st.subheader("// LICENSE_PERFORMANCE_MATRIX (LAST 7 DAYS)")
        
        # Get dates for the last 7 days
        today = datetime.now().date()
        date_list = [today - timedelta(days=i) for i in range(1, 8)]
        date_strs = [d.strftime('%Y-%m-%d') for d in date_list]
        
        # Filter data for last 7 days
        df_7d = df[df['date'].isin(date_list)]
        
        # Pivot Table: Licenses as rows, Dates as columns
        pivot_7d = df_7d.pivot_table(
            index='LIC_ID', 
            columns='date', 
            values='usd_amount', 
            aggfunc='sum'
        ).fillna(0)
        
        # Calculate License Totals
        license_totals = df.groupby('LIC_ID')['usd_amount'].sum().rename('TOTAL_EARNED')
        
        # Merge Totals with Pivot
        final_matrix = pd.merge(license_totals, pivot_7d, left_index=True, right_index=True, how='right')
        
        # Sort by total earned
        final_matrix = final_matrix.sort_values('TOTAL_EARNED', ascending=False)

        # Style the dataframe for the dashboard
        st.dataframe(
            final_matrix,
            column_config={
                "TOTAL_EARNED": st.column_config.NumberColumn("TOTAL ($)", format="$ %.4f"),
                **{d: st.column_config.NumberColumn(d.strftime('%b %d'), format="$ %.4f") for d in date_list}
            },
            use_container_width=True
        )

        # 4. TIME SERIES FLOW
        st.markdown("---")
        st.subheader("// REWARD_VELOCITY_OVER_TIME")
        daily_flow = df.set_index('timestamp').resample('D')['usd_amount'].sum().reset_index()
        fig_flow = px.area(daily_flow, x='timestamp', y='usd_amount', template="plotly_dark")
        fig_flow.update_traces(line_color='#00f2ff', fillcolor='rgba(0, 242, 255, 0.1)')
        st.plotly_chart(fig_flow, use_container_width=True)

    else:
        st.error(f"📡 OFFLINE: {err}")
else:
    st.info("👈 Waiting for Token. Please paste your Bearer token in the sidebar.")
