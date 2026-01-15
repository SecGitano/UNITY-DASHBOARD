import streamlit as st
import pandas as pd
import plotly.express as px
import json

# 1. Setup & Styling
st.set_page_config(page_title="Unity Node Monitor", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    div[data-testid="stMetric"] {
        background-color: #1A1C24;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 10px;
    }
    [data-testid="stMetricValue"] { color: #00FFCC !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [aria-selected="true"] { background-color: #00FFCC !important; color: black !important; }
</style>
""", unsafe_allow_html=True)

# 2. Sidebar
with st.sidebar:
    st.header("⚡ Settings")
    uploaded_file = st.file_uploader("Upload JSON .txt", type=['txt', 'json'])
    token_price = st.number_input("Token Price ($)", value=0.0125, format="%.4f")

# 3. App Logic
if uploaded_file:
    try:
        data = json.load(uploaded_file)
        df = pd.DataFrame(data)
        df['createdAt'] = pd.to_datetime(df['createdAt'])
        df['date'] = df['createdAt'].dt.date
        df['tokens'] = df['amountMicros'] / 1000000

        st.title("🚀 Rewards Dashboard")
        
        # Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Tokens", f"{df['tokens'].sum():,.2f}")
        m2.metric("USD Value", f"${(df['tokens'].sum() * token_price):,.2f}")
        m3.metric("Daily Avg", f"{(df['tokens'].sum() / df['date'].nunique()):,.2f}")
        m4.metric("Licenses", df['licenseId'].nunique())

        # Tabs
        tab1, tab2, tab3 = st.tabs(["📊 Trends", "🔍 License Drill-down", "📜 Logs"])

        with tab1:
            c1, c2 = st.columns([2, 1])
            with c1:
                daily = df.groupby('date')['tokens'].sum().reset_index()
                fig1 = px.area(daily, x='date', y='tokens', template='plotly_dark', color_discrete_sequence=['#00FFCC'], title="Daily Growth")
                st.plotly_chart(fig1, use_container_width=True)
            with c2:
                nodes = df.groupby('nodeId')['tokens'].sum().reset_index().sort_values('tokens', ascending=False).head(10)
                fig2 = px.bar(nodes, x='tokens', y='nodeId', orientation='h', template='plotly_dark', title="Top Nodes")
                fig2.update_layout(yaxis={'visible': False})
                st.plotly_chart(fig2, use_container_width=True)

        with tab2:
            selection = st.selectbox("Select License ID", df['licenseId'].unique())
            lic_df = df[df['licenseId'] == selection].sort_values('createdAt')
            st.info(f"Earned: {lic_df['tokens'].sum():,.4f} | Events: {len(lic_df)}")
            fig3 = px.line(lic_df, x='createdAt', y='tokens', template='plotly_dark', title="License History")
            st.plotly_chart(fig3, use_container_width=True)

        with tab3:
            st.dataframe(df[['createdAt', 'licenseId', 'nodeId', 'tokens']].sort_values('createdAt', ascending=False), use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("👈 Please upload your rewards file in the sidebar to start.")
