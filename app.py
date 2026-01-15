import streamlit as st
import pandas as pd
import plotly.express as px
import json

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Unity Node Monitor", layout="wide", initial_sidebar_state="expanded")

# --- 2. DARK MODE CSS STYLING ---
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #0E1117;
    }
    
    /* Metrics (Cards) */
    div[data-testid="stMetric"] {
        background-color: #262730;
        border: 1px solid #41444C;
        padding: 15px 20px;
        border-radius: 10px;
        color: white;
    }
    
    /* Text Colors */
    [data-testid="stMetricLabel"] {
        color: #979797 !important;
    }
    [data-testid="stMetricValue"] {
        color: #00FFAA !important; /* Neon Green */
        font-size: 26px !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        color: #FFFFFF;
    }
    .stTabs [aria-selected="true"] {
        background-color: #262730;
        border-bottom: 2px solid #00FFAA;
        color: #00FFAA;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.header("⚡ Node Settings")
    uploaded_file = st.file_uploader("Upload JSON File", type=['txt', 'json'])
    st.divider()
    token_price = st.number_input("Token Price ($)", value=0.0125, format="%.4f")
    st.info("💡 Tip: Double-click the chart to reset the zoom.")

# --- 4. MAIN APP ---
if uploaded_file is not None:
    try:
        # Load & Clean Data
        data = json.load(uploaded_file)
        df = pd.DataFrame(data)
        
        # Transformations
        df['createdAt'] = pd.to_datetime(df['createdAt'])
        df['date'] = df['createdAt'].dt.date
        df['tokens'] = df['amountMicros'] / 1000000
        df['usd_value'] = df['tokens'] * token_price

        # Header
        st.title("🚀 Rewards Dashboard")
        st.markdown(f"**Status:** Tracking {len(df)} Reward Events")

        # --- TOP METRICS ROW ---
        total_tokens = df['tokens'].sum()
        total_usd = total_tokens * token_price
        active_nodes = df['nodeId'].nunique()
        best_day = df.groupby('date')['tokens'].sum().max()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Balance", f"{total_tokens:,.2f} 🪙")
        c2.metric("Portfolio Value", f"${total_usd:,.2f}")
        c3.metric("Active Nodes", f"{active_nodes}")
        c4.metric("Best Day", f"{best_day:,.2f} 🪙")

        st.divider()

        # --- TABS ---
        tab1, tab2, tab3 = st.tabs(["📈 Growth Chart", "🔍 Node Performance", "📝 Log Data"])

        # TAB 1: Main Chart
        with tab1:
            st.subheader("Accumulated Rewards")
            daily_
