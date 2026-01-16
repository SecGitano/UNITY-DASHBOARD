import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# --- SETUP & CONFIGURATION ---
URL = "https://api.unityedge.io/rest/v1/rpc/rewards_get_allocations"

HEADERS = {
    "authority": "api.unityedge.io",
    "apikey": "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c",
    "authorization": "Bearer eyJhbGciOiJIUzI1NiIsImtpZCI6InlHbDE2UkxxLzBzTGxac0ciLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3Z0bGxwYWd0bW5jYmt5d3NxY2NkLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI3ZWZmZWM2Zi1iYWJmLTQ0MDYtYWY0MC1hZGYxYWJlYWZlMzEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY4NjAyNjg0LCJpYXQiOjE3Njg1OTkwODQsImVtYWlsIjoiIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJ3ZWIzIiwicHJvdmlkZXJzIjpbIndlYjMiXX0sInVzZXJfbWV0YWRhdGEiOnsiY3VzdG9tX2NsYWltcyI6eyJhZGRyZXNzIjoiMHg1NmYxMTM2Y2EwMjkxZjJiYmEwZTBiOTRjY2VmNDAzMzkzZDg1Y2EyIiwiY2hhaW4iOiJldGhlcmV1bSIsImRvbWFpbiI6InVuaXR5bm9kZXMuaW8iLCJuZXR3b3JrIjoiODY5Iiwic3RhdGVtZW50IjpudWxsfSwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IndlYjM6ZXRoZXJldW06MHg1NmYxMTM2Y2EwMjkxZjJiYmEwZTBiOTRjY2VmNDAzMzkzZDg1Y2EyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoid2ViMyIsInRpbWVzdGFtcCI6MTc2NzcyNjA3NH1dLCJzZXNzaW9uX2lkIjoiZjc0MThmNTUtMzE5Ni00OWQwLTgyYjUtZGY5YWFlN2E1ZTE0IiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.wJbFwqzhRdaRsofgFhiSGO_OK_h80hCT3M3b1qV7Nsg",
    "content-type": "application/json",
    "accept": "*/*"
}

# This matches the payload you found
PAYLOAD = {
    "skip": None, 
    "take": None
}

st.set_page_config(page_title="UnityNodes Live Dashboard", layout="wide")

st.title("🛡️ UnityNodes Rewards Monitor")
st.caption("Tracking allocations for wallet: 0x56f...5ca2")

# --- DATA FETCHING ---
@st.cache_data(ttl=600) # Caches data for 10 minutes to be efficient
def get_unity_data():
    try:
        response = requests.post(URL, headers=HEADERS, json=PAYLOAD)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Server returned error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None

data = get_unity_data()

if data:
    df = pd.DataFrame(data)
    
    # Pre-processing: Convert numeric and date columns
    # We use 'errors=ignore' in case the column names vary slightly
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'])
    
    # --- KEY METRICS ---
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Allocations", len(df))
    
    # Assuming 'amount' is the column name for rewards
    reward_col = next((c for c in df.columns if 'amount' in c.lower() or 'reward' in c.lower()), None)
    if reward_col:
        df[reward_col] = pd.to_numeric(df[reward_col])
        with col2:
            st.metric("Total Earned", f"{df[reward_col].sum():,.2f}")
        with col3:
            st.metric("Avg Per Allocation", f"{df[reward_col].mean():,.2f}")
    
    # --- CHARTS ---
    st.markdown("---")
    if 'created_at' in df.columns and reward_col:
        st.subheader("📈 Earning History")
        # Create a time-series chart
        fig = px.line(df.sort_values('created_at'), x='created_at', y=reward_col, 
                      title="Rewards Over Time", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    # --- RAW DATA TABLE ---
    st.subheader("📋 Recent Records")
    st.dataframe(df, use_container_width=True)

    # --- CSV DOWNLOAD ---
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Export Data to Excel/CSV", csv, "unity_data.csv", "text/csv")

else:
    st.info("No data returned. Make sure your nodes are active and generating rewards.")
