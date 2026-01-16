import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION (Ensure these match exactly) ---
URL = "https://api.unityedge.io/rest/v1/rpc/rewards_get_allocations"

# I added more headers here to mimic your browser exactly
HEADERS = {
    "authority": "api.unityedge.io",
    "accept": "*/*",
    "apikey": "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c",
    "authorization": "Bearer eyJhbGciOiJIUzI1NiIsImtpZCI6InlHbDE2UkxxLzBzTGxac0ciLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3Z0bGxwYWd0bW5jYmt5d3NxY2NkLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI3ZWZmZWM2Zi1iYWJmLTQ0MDYtYWY0MC1hZGYxYWJlYWZlMzEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY4NjAyNjg0LCJpYXQiOjE3Njg1OTkwODQsImVtYWlsIjoiIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJ3ZWIzIiwicHJvdmlkZXJzIjpbIndlYjMiXX0sInVzZXJfbWV0YWRhdGEiOnsiY3VzdG9tX2NsYWltcyI6eyJhZGRyZXNzIjoiMHg1NmYxMTM2Y2EwMjkxZjJiYmEwZTBiOTRjY2VmNDAzMzkzZDg1Y2EyIiwiY2hhaW4iOiJldGhlcmV1bSIsImRvbWFpbiI6InVuaXR5bm9kZXMuaW8iLCJuZXR3b3JrIjoiODY5Iiwic3RhdGVtZW50IjpudWxsfSwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJwaG9uZV92ZXJpZmllZCI6ZmFsc2UsInN1YiI6IndlYjM6ZXRoZXJldW06MHg1NmYxMTM2Y2EwMjkxZjJiYmEwZTBiOTRjY2VmNDAzMzkzZDg1Y2EyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoid2ViMyIsInRpbWVzdGFtcCI6MTc2NzcyNjA3NH1dLCJzZXNzaW9uX2lkIjoiZjc0MThmNTUtMzE5Ni00OWQwLTgyYjUtZGY5YWFlN2E1ZTE0IiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.wJbFwqzhRdaRsofgFhiSGO_OK_h80hCT3M3b1qV7Nsg",
    "content-type": "application/json",
    "origin": "https://manage.unitynodes.io",
    "referer": "https://manage.unitynodes.io/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

PAYLOAD = {"skip": None, "take": None}

st.set_page_config(page_title="UNITY CORE", layout="wide")

# --- IMPROVED FETCH FUNCTION WITH DEBUGGING ---
def fetch_data():
    try:
        # Use a timeout so the app doesn't hang forever
        response = requests.post(URL, headers=HEADERS, json=PAYLOAD, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if not data:
                st.warning("Connection successful, but the account returned 0 allocations.")
                return None
            df = pd.DataFrame(data)
            # Ensure columns are the right format
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at'])
            if 'amount' in df.columns:
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            return df
        
        else:
            # THIS WILL SHOW YOU EXACTLY WHAT IS WRONG
            st.error(f"📡 API CONNECTION FAILED")
            st.info(f"Status Code: {response.status_code}")
            with st.expander("View Server Error Detail"):
                st.write(response.text)
            return None
            
    except requests.exceptions.Timeout:
        st.error("Request Timed Out. The server is taking too long to respond.")
    except Exception as e:
        st.error(f"Connection Error: {str(e)}")
    return None

# --- RUN DASHBOARD ---
df = fetch_data()

if df is not None:
    st.success("SYNCHRONIZED SUCCESSFULLY")
    # ... (Rest of your dashboard code here) ...
    st.dataframe(df)
