import streamlit as st
import pandas as pd
import plotly.express as px
import json

# --- 1. CONFIG & DASH DARK THEME ---
st.set_page_config(page_title="Unity Node Monitor", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #FFFFFF; }
    /* Card Style */
    div[data-testid="column"] {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    /* Hide default metric padding */
    div[data-testid="stMetric"] { background: none; border: none; padding: 0; }
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #161B22; border: 1px solid #30363D; 
        border-radius: 8px; padding: 10px 20px; color: #8B949E;
    }
    .stTabs [aria-selected="true"] { border-color: #58A6FF; color: #58A6FF; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR & UPLOAD ---
with st.sidebar:
    st.image("https://img.icons8.com/nolan/64/cyber-security.png")
    st.title("DashDark Unity")
    uploaded_file = st.file_uploader("Reward JSON", type=['txt', 'json'])
    token_price = st.number_input("Token Price ($)", value=0.0125, format="%.4f")
    st.divider()

# --- 3. MAIN APP LOGIC ---
if uploaded_file:
    try:
        df = pd.DataFrame(json.load(uploaded_file))
        df['createdAt'] = pd.to_datetime(df['createdAt'])
        df['date'] = df['createdAt'].dt.date
        df['tokens'] = df['amountMicros'] / 1000000
        
        st.title("🖥️ Node Command Center")
        
        # --- TOP METRIC CARDS ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("TOTAL REWARDS", f"{df['tokens'].sum():,.2f}")
        c2.metric("USD VALUE", f"${(df['tokens'].sum()*token_price):,.2f}")
        c3.metric("NODES", df['nodeId'].nunique())
        c4.metric("DAYS", df['date'].nunique())

        # --- TABS ---
        t1, t2, t3 = st.tabs(["📊 ANALYTICS", "🏆 PERFORMANCE", "📜 LOGS"])

        with t1:
            daily = df.groupby('date')['tokens'].sum().reset_index()
            fig = px.area(daily, x='date', y='tokens', title="Earnings Momentum")
            fig.update_traces(line_color='#58A6FF', fillcolor='rgba(88, 166, 255, 0.1)')
            fig.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

        with t2:
            st.subheader("Performance by License")
            top_lic = df.groupby('licenseId')['tokens'].sum().sort_values(ascending=False).head(10).reset_index()
            fig2 = px.bar(top_lic, x='tokens', y='licenseId', orientation='h', color='tokens', color_continuous_scale='Blues')
            fig2.update_layout(template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis={'visible':False})
            st.plotly_chart(fig2, use_container_width=True)

            sel = st.selectbox("Drill-down License", df['licenseId'].unique())
            st.dataframe(df[df['licenseId']==sel][['createdAt', 'tokens']].sort_values('createdAt', ascending=False), use_container_width=True)

        with t3:
            st.dataframe(df[['createdAt', 'licenseId', 'tokens']].sort_values('createdAt', ascending=False), use_container_width=True)

    except Exception as e:
        st.error(f"Logic Error: {e}")
else:
    st.info("👈 Please upload your Unity Rewards JSON to begin.")
