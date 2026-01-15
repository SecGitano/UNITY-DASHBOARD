import streamlit as st
import pandas as pd
import json

# Set page to wide mode
st.set_page_config(page_title="Unity Node Rewards", layout="wide")

st.title("📱 Unity Node Rewards Dashboard")
st.markdown("Upload your rewards JSON text file to see your performance.")

# --- SIDEBAR: File Upload ---
st.sidebar.header("Data Upload")
uploaded_file = st.sidebar.file_uploader("Choose your rewards .txt file", type=['txt', 'json'])

if uploaded_file is not None:
    try:
        # Load JSON data
        data = json.load(uploaded_file)
        df = pd.DataFrame(data)

        # --- DATA PROCESSING ---
        # Convert timestamp to readable date
        df['createdAt'] = pd.to_datetime(df['createdAt'])
        df['date_only'] = df['createdAt'].dt.date
        
        # Convert amountMicros to standard Token units (1,000,000 micros = 1 Token)
        df['tokens'] = df['amountMicros'] / 1000000

        # --- METRICS CALCULATIONS ---
        total_tokens = df['tokens'].sum()
        active_nodes = df['nodeId'].nunique()
        active_licenses = df['licenseId'].nunique()
        days_count = df['date_only'].nunique()
        avg_daily = total_tokens / days_count if days_count > 0 else 0

        # --- DISPLAY TOP METRICS ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Tokens", f"{total_tokens:,.2f}")
        col2.metric("Active Nodes", active_nodes)
        col3.metric("Licenses", active_licenses)
        col4.metric("Daily Avg", f"{avg_daily:,.2f}")

        st.divider()

        # --- VISUALIZATIONS ---
        row2_col1, row2_col2 = st.columns(2)

        with row2_col1:
            st.subheader("📈 Earnings Over Time")
            daily_rev = df.groupby('date_only')['tokens'].sum()
            st.area_chart(daily_rev)

        with row2_col2:
            st.subheader("🏆 Top Performing Licenses")
            # Group by licenseId to see which one makes the most
            license_ranking = df.groupby('licenseId')['tokens'].sum().sort_values(ascending=False).head(10)
            st.bar_chart(license_ranking)

        # --- DATA TABLE ---
        st.subheader("📋 Detailed Records (Latest First)")
        # Show specific columns for clarity
        display_df = df[['createdAt', 'nodeId', 'licenseId', 'tokens']].sort_values(by='createdAt', ascending=False)
        st.dataframe(display_df, use_container_width=True)

    except Exception as e:
        st.error(f"Error processing file: {e}")
        st.info("Ensure your file starts with '[' and ends with ']' and is valid JSON.")

else:
    st.info("👈 Please upload your rewards .txt file in the sidebar to generate the dashboard.")
