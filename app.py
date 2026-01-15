import streamlit as st
import pandas as pd
import plotly.express as px
import json

# 1. Page Configuration
st.set_page_config(page_title="Unity Node Pro Dashboard", layout="wide", initial_sidebar_state="expanded")

# 2. Custom CSS for Dark Theme & Cards
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #00FFCC; }
    div.stMetric {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #333;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
    .main { background-color: #0E1117; }
    </style>
    """, unsafe_allow_html=True)

# 3. Sidebar
st.sidebar.title("💎 Unity Node Pro")
uploaded_file = st.sidebar.file_uploader("Upload rewards .txt file", type=['txt', 'json'])
token_price = st.sidebar.number_input("Token Price (USD)", value=0.00, format="%.4f")

# 4. Helper Function: Load Data
@st.cache_data
def process_data(file):
    data = json.load(file)
    df = pd.DataFrame(data)
    df['createdAt'] = pd.to_datetime(df['createdAt'])
    df['date'] = df['createdAt'].dt.date
    df['tokens'] = df['amountMicros'] / 1000000
    if token_price > 0:
        df['usd_val'] = df['tokens'] * token_price
    return df

# 5. Dashboard Logic
if uploaded_file:
    df = process_data(uploaded_file)
    
    # --- HEADER STATS ---
    total_tokens = df['tokens'].sum()
    unique_licenses = df['licenseId'].nunique()
    total_usd = total_tokens * token_price
    
    st.title("📊 Node Rewards Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tokens", f"{total_tokens:,.2f} 🟢")
    with col2:
        st.metric("Active Licenses", f"{unique_licenses}")
    with col3:
        st.metric("Total USD", f"${total_usd:,.2f}")
    with col4:
        st.metric("Avg Reward", f"{(total_tokens/df['date'].nunique()):,.2f}")

    # --- TABS SYSTEM ---
    tab1, tab2, tab3 = st.tabs(["📈 Growth & Trends", "🏆 License Rankings", "📋 Raw Records"])

    with tab1:
        st.subheader("Rewards Accumulation (Interactive)")
        daily_rev = df.groupby('date')['tokens'].sum().reset_index()
        
        # Interactive Plotly Chart
        fig = px.area(daily_rev, x='date', y='tokens', 
                      title="Daily Token Generation",
                      color_discrete_sequence=['#00FFCC'])
        fig.update_layout(template="plotly_dark", hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Performance by License")
        license_df = df.groupby('licenseId')['tokens'].sum().sort_values(ascending=False).reset_index()
        
        # Interactive Bar Chart
        fig2 = px.bar(license_df.head(15), x='tokens', y='licenseId', 
                      orientation='h', color='tokens',
                      title="Top 15 Licenses",
                      color_continuous_scale='Viridis')
        fig2.update_layout(template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)
        
        # Dropdown to inspect a specific License
        st.divider()
        selected_license = st.selectbox("🔍 Select a License to Drill Down:", df['licenseId'].unique())
        specific_license_data = df[df['licenseId'] == selected_license]
        st.write(f"History for License: {selected_license}")
        st.dataframe(specific_license_data[['createdAt', 'tokens']].sort_values(by='createdAt', ascending=False))

    with tab3:
        st.subheader("Complete Log History")
        st.write("Use the search icon on the table to find specific Node IDs or dates.")
        st.dataframe(df[['createdAt', 'licenseId', 'nodeId', 'tokens']].sort_values(by='createdAt', ascending=False), use_container_width=True)

else:
    st.info("👋 Welcome! Please upload your Unity rewards .txt file in the sidebar to populate the dashboard.")
    # Show a placeholder image or some instructions
    st.image("https://images.unsplash.com/photo-1639762681485-074b7f938ba0?auto=format&fit=crop&q=80&w=1000", caption="Unity Node Monitoring Powered by AI")
