import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIG ---
BASE_URL = "https://api.unityedge.io/rest/v1/rpc"
URL_ALLOCATIONS = f"{BASE_URL}/rewards_get_allocations"
URL_BALANCE = f"{BASE_URL}/rewards_get_balance"

RAW_TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6InlHbDE2UkxxLzBzTGxac0ciLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3Z0bGxwYWd0bW5jYmt5d3NxY2NkLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI3ZWZmZWM2Zi1iYWJmLTQ0MDYtYWY0MC1hZGYxYWJlYWZlMzEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY4NjAyNjg0LCJpYXQiOjE3Njg1OTkwODQsImVtYWlsIjoiIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJ3ZWIzIiwicHJvdmlkZXJzIjpbIndlYjMiXX0sInVzZXJfbWV0YWRhdGEiOnsiY3VzdG9tX2NsYWltcyI6eyJhZGRyZXNzIjoiMHg1NmYxMTM2Y2EwMjkxZjJiYmEwZTBiOTRjY2VmNDAzMzkzZDg1Y2EyIiwiY2hhaW4iOiJldGhlcmV1bSIsImRvbWFpbiI6InVuaXR5bm9kZXMuaW8iLCJuZXR3b3JrIjoiODY5Iiwic3RhdGVtZW50IjpudWxsfSwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IndlYjM6ZXRoZXJldW06MHg1NmYxMTM2Y2EwMjkxZjJiYmEwZTBiOTRjY2VmNDAzMzkzZDg1Y2EyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoid2ViMyIsInRpbWVzdGFtcCI6MTc2NzcyNjA3NH1dLCJzZXNzaW9uX2lkIjoiZjc0MThmNTUtMzE5Ni00OWQwLTgyYjUtZGY5YWFlN2E1ZTE0IiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.wJbFwqzhRdaRsofgFhiSGO_OK_h80hCT3M3b1qV7Nsg"

HEADERS = {
    "authority": "api.unityedge.io",
    "apikey": "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c",
    "authorization": f"Bearer {RAW_TOKEN}",
    "content-type": "application/json",
    "user-agent": "Mozilla/5.0"
}

st.set_page_config(page_title="UNITY_CORE // TERMINAL", layout="wide")

# --- DATA FETCHING ---

def get_allocations():
    """Fetches history records"""
    try:
        r = requests.post(URL_ALLOCATIONS, headers=HEADERS, json={"skip": None, "take": None}, timeout=10)
        if r.status_code == 200:
            df = pd.DataFrame(r.json())
            # Clean columns
            date_col = next((c for c in df.columns if 'created' in c or 'time' in c), None)
            amt_col = next((c for c in df.columns if 'amount' in c or 'reward' in c), None)
            if date_col and amt_col:
                df['timestamp'] = pd.to_datetime(df[date_col])
                df['usd_amount'] = pd.to_numeric(df[amt_col]) / 1_000_000
                return df
        return None
    except Exception as e:
        st.error(f"Allocations Error: {e}")
        return None

def get_true_balance():
    """Fetches total balance from the summary endpoint"""
    try:
        r = requests.post(URL_BALANCE, headers=HEADERS, json={}, timeout=10)
        data = r.json()
        
        # Supabase RPCs often return a list with one object: [{"rewards_get_balance": 234000000}]
        if isinstance(data, list) and len(data) > 0:
            # Try to find a numeric value in the first item
            first_item = data[0]
            # It might be named 'balance' or the name of the function
            val = first_item.get('balance') or first_item.get('rewards_get_balance') or list(first_item.values())[0]
            return float(val) / 1_000_000
        return None
    except Exception as e:
        # We don't crash the app here, just return None
        return None

# --- EXECUTION ---

df = get_allocations()
true_balance = get_true_balance()

# --- UI RENDER ---

st.markdown("<h1 style='color:#00f2ff;'>UNITY_CORE <span style='color:white;'>TERMINAL</span></h1>", unsafe_allow_html=True)

if df is not None:
    # SUCCESS: Dashboard display
    m1, m2, m3 = st.columns(3)
    
    # Use true_balance if we got it, otherwise fall back to the sum of allocations
    display_total = true_balance if true_balance is not None else df['usd_amount'].sum()
    
    m1.metric("TOTAL BALANCE", f"${display_total:,.2f} USD")
    m2.metric("RECORDS FOUND", len(df))
    m3.metric("STATUS", "ONLINE" if true_balance else "PARTIAL SYNC")

    # Chart
    daily = df.set_index('timestamp').resample('D')['usd_amount'].sum().reset_index()
    fig = px.area(daily, x='timestamp', y='usd_amount', template="plotly_dark")
    fig.update_traces(line_color='#00f2ff', fillcolor='rgba(0, 242, 255, 0.1)')
    st.plotly_chart(fig, use_container_width=True)

    # Raw Data
    st.dataframe(df.sort_values('timestamp', ascending=False), use_container_width=True)

    if true_balance is None:
        st.info("💡 Note: Total Balance endpoint is currently unreachable. Showing sum of history instead.")

else:
    # FAILURE: Show raw debug info
    st.error("📡 CORE_SYNC_FAILURE")
    st.write("The script could not retrieve your allocation history.")
    
    with st.expander("🛠️ DEBUG: VIEW RAW API RESPONSES"):
        st.write("Testing connection to Allocations...")
        test_r = requests.post(URL_ALLOCATIONS, headers=HEADERS, json={"skip": None, "take": None})
        st.write(f"Status: {test_r.status_code}")
        st.json(test_r.json())
        
        st.write("Testing connection to Balance...")
        test_b = requests.post(URL_BALANCE, headers=HEADERS, json={})
        st.write(f"Status: {test_b.status_code}")
        st.json(test_b.json())
