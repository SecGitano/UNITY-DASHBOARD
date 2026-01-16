import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIG ---
URL = "https://api.unityedge.io/rest/v1/rpc/rewards_get_allocations"
RAW_TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6InlHbDE2UkxxLzBzTGxac0ciLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3Z0bGxwYWd0bW5jYmt5d3NxY2NkLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI3ZWZmZWM2Zi1iYWJmLTQ0MDYtYWY0MC1hZGYxYWJlYWZlMzEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY4NjAyNjg0LCJpYXQiOjE3Njg1OTkwODQsImVtYWlsIjoiIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJ3ZWIzIiwicHJvdmlkZXJzIjpbIndlYjMiXX0sInVzZXJfbWV0YWRhdGEiOnsiY3VzdG9tX2NsYWltcyI6eyJhZGRyZXNzIjoiMHg1NmYxMTM2Y2EwMjkxZjJiYmEwZTBiOTRjY2VmNDAzMzkzZDg1Y2EyIiwiY2hhaW4iOiJldGhlcmV1bSIsImRvbWFpbiI6InVuaXR5bm9kZXMuaW8iLCJuZXR3b3JrIjoiODY5Iiwic3RhdGVtZW50IjpudWxsfSwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IndlYjM6ZXRoZXJldW06MHg1NmYxMTM2Y2EwMjkxZjJiYmEwZTBiOTRjY2VmNDAzMzkzZDg1Y2EyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoid2ViMyIsInRpbWVzdGFtcCI6MTc2NzcyNjA3NH1dLCJzZXNzaW9uX2lkIjoiZjc0MThmNTUtMzE5Ni00OWQwLTgyYjUtZGY5YWFlN2E1ZTE0IiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.wJbFwqzhRdaRsofgFhiSGO_OK_h80hCT3M3b1qV7Nsg"

HEADERS = {
    "authority": "api.unityedge.io",
    "apikey": "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c",
    "authorization": f"Bearer {RAW_TOKEN}",
    "content-type": "application/json",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

st.set_page_config(page_title="UNITY_CORE // TERMINAL", layout="wide")

# --- DATA ENGINE ---
def load_data():
    try:
        response = requests.post(URL, headers=HEADERS, json={"skip": None, "take": None}, timeout=10)
        
        # 1. Check if the server actually liked the request
        if response.status_code != 200:
            return None, f"Server Error {response.status_code}: {response.text}"
        
        raw_json = response.json()
        
        # 2. Check if the response is a list (valid data) or a dict (usually an error)
        if isinstance(raw_json, dict) and "message" in raw_json:
            return None, f"API Message: {raw_json['message']}"
            
        df = pd.DataFrame(raw_json)
        
        if df.empty:
            return None, "Empty dataset returned from account."

        # 3. DYNAMIC COLUMN DETECTION (The Fix)
        # We look for ANY column that looks like a date or an amount
        date_col = next((c for c in df.columns if 'created' in c or 'time' in c or 'date' in c), None)
        amt_col = next((c for c in df.columns if 'amount' in c or 'reward' in c or 'value' in c), None)
        
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.rename(columns={date_col: 'created_at'})
        if amt_col:
            df[amt_col] = pd.to_numeric(df[amt_col], errors='coerce')
            df = df.rename(columns={amt_col: 'amount'})
            
        return df, 200
    except Exception as e:
        return None, str(e)

df, status_msg = load_data()

# --- RENDER ---
st.markdown("<h1 style='color: #00f2ff;'>UNITY_CORE <span style='color: white;'>TERMINAL</span></h1>", unsafe_allow_html=True)

if df is not None:
    # SUCCESS: Build Dashboard
    m1, m2, m3 = st.columns(3)
    m1.metric("TOTAL REWARDS", f"{df['amount'].sum():,.2f} ₮")
    m2.metric("TOTAL PACKETS", len(df))
    m3.metric("STATUS", "SYNCHRONIZED", delta="LIVE")

    st.markdown("---")
    
    # Area Chart
    daily = df.set_index('created_at').resample('D')['amount'].sum().reset_index()
    fig = px.area(daily, x='created_at', y='amount', template="plotly_dark", title="// REWARD_FLOW")
    fig.update_traces(line_color='#00f2ff', fillcolor='rgba(0, 242, 255, 0.1)')
    st.plotly_chart(fig, use_container_width=True)

    # Table
    st.dataframe(df.sort_values('created_at', ascending=False), use_container_width=True)

else:
    # FAILURE: Show Debugger
    st.error(f"📡 SYSTEM OFFLINE")
    st.warning(f"Reason: {status_msg}")
    
    with st.expander("🛠️ DEBUG DATA (What did the server send?)"):
        st.write("If you see an error message below, your Bearer token might be expired.")
        # Try one more raw fetch to show the user the output
        try:
            debug_res = requests.post(URL, headers=HEADERS, json={"skip": None, "take": None})
            st.json(debug_res.json())
        except:
            st.write("Could not even connect to debug.")
