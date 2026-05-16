import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# ==================================
# CONFIG
# ==================================
API_URL_BAL = "https://api.unityedge.io/rest/v1/rpc/rewards_get_balance"
API_URL_HIS = "https://api.unityedge.io/rest/v1/rpc/rewards_get_allocations"
API_KEY = "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c"

st.set_page_config(
    page_title="Unity Analytics",
    layout="wide",
    page_icon="🌙"
)

# ==================================
# DARK UI
# ==================================
st.markdown("""
<style>
.stApp {
    background:#0f172a;
    color:#e2e8f0;
}

h1,h2,h3 { color:#f8fafc !important; }

[data-testid="stSidebar"]{
    background:#020617;
}

[data-testid="stMetric"]{
    background:#1e293b;
    border:1px solid #334155;
    border-radius:12px;
    padding:20px;
}

.card {
    background:#1e293b;
    padding:20px;
    border-radius:12px;
    border:1px solid #334155;
}

.status-grid{
    display:grid;
    grid-template-columns:repeat(auto-fill,minmax(40px,1fr));
    gap:6px;
}

.status-box{
    padding:8px;
    text-align:center;
    border-radius:6px;
    font-size:12px;
}

.green{background:#14532d;color:#bbf7d0;}
.yellow{background:#713f12;color:#fde68a;}
.red{background:#7f1d1d;color:#fecaca;}
</style>
""", unsafe_allow_html=True)

# ==================================
# HELPERS
# ==================================
def format_id(v):
    s = str(v)
    return s if len(s) <= 10 else f"{s[:4]}...{s[-4:]}"


def parse_balance(data):
    try:
        if isinstance(data, (int, float)):
            return float(data)

        if isinstance(data, list) and data:
            item = data[0]
            if isinstance(item, dict):
                return float(next(iter(item.values())))
        return 0.0
    except:
        return 0.0


# ==================================
# DATA ENGINE
# ==================================
@st.cache_data(ttl=600)
def deep_sync(token):

    headers = {
        "apikey": API_KEY,
        "authorization": f"Bearer {token}",
        "content-type": "application/json"
    }

    try:
        r_bal = requests.post(API_URL_BAL, headers=headers, json={})
        balance = parse_balance(r_bal.json()) / 1_000_000

        rows = []
        skip = 0

        while True:
            r = requests.post(
                API_URL_HIS,
                headers=headers,
                json={"skip": skip, "take": 1000}
            )

            data = r.json()
            if not data:
                break

            rows.extend(data)

            if len(data) < 1000:
                break

            skip += 1000

        if not rows:
            return None, 0, "No data"

        df = pd.DataFrame(rows)

        d_col = next(c for c in df.columns if "time" in c.lower() or "created" in c.lower())
        a_col = next(c for c in df.columns if "amount" in c.lower() or "reward" in c.lower())
        node_col = next(c for c in df.columns if "node" in c.lower())
        lic_col = next(c for c in df.columns if "license" in c.lower())

        df["timestamp"] = pd.to_datetime(df[d_col], errors="coerce", utc=True).dt.tz_localize(None)
        df = df.dropna(subset=["timestamp"])

        df["usd_amount"] = pd.to_numeric(df[a_col], errors="coerce").fillna(0) / 1_000_000
        df["date_only"] = df["timestamp"].dt.date

        df["NODE_RAW"] = df[node_col]
        df["LIC_RAW"] = df[lic_col]

        df["NODE_ID"] = df["NODE_RAW"].apply(format_id)

        return df, balance, None

    except Exception as e:
        return None, 0, str(e)


# ==================================
# AUTH (TEMP SIMPLE VERSION)
# ==================================
with st.sidebar:
    st.markdown("## Hando")

    token = st.text_input(
        "Unity JWT Token",
        type="password"
    )

    st.caption(
        "Login is handled via MetaMask on Unity portal for now"
    )

    if st.button("Refresh"):
        st.cache_data.clear()
        st.rerun()


# ==================================
# MAIN
# ==================================
st.title("Analytics Overview")

if token:

    df, balance, err = deep_sync(token)

    if df is None:
        st.error(err)

    else:

        now = datetime.now()
        week = now.date() - timedelta(days=7)
        yesterday = now.date() - timedelta(days=1)

        rev7 = df[df["date_only"] >= week]["usd_amount"].sum()
        rev1 = df[df["date_only"] == yesterday]["usd_amount"].sum()

        c1, c2, c3 = st.columns(3)

        c1.metric("Wallet", f"${balance:,.2f}")
        c2.metric("7D Revenue", f"${rev7:,.2f}")
        c3.metric("Yesterday", f"${rev1:,.4f}")

        # =====================
        # LICENSE STATUS
        # =====================
        st.subheader("License Status")

        active = set(df["LIC_RAW"].unique())

        st.metric("Active Licenses", len(active))

        # =====================
        # HEARTBEAT GRID
        # =====================
        st.subheader("Heartbeat")

        payouts = df.groupby("LIC_RAW")["timestamp"].max().to_dict()

        html = '<div class="status-grid">'

        for i, lic in enumerate(active, 1):

            hrs = (now - payouts[lic]).total_seconds() / 3600

            if hrs <= 48:
                cls = "green"
            elif hrs <= 96:
                cls = "yellow"
            else:
                cls = "red"

            html += f'<div class="status-box {cls}">#{i}</div>'

        html += "</div>"

        st.markdown(html, unsafe_allow_html=True)

        # =====================
        # REVENUE CHART
        # =====================
        st.subheader("Revenue")

        daily = df.groupby("date_only")["usd_amount"].sum().reset_index()

        fig = px.area(daily, x="date_only", y="usd_amount")

        st.plotly_chart(fig, use_container_width=True)

        # =====================
        # NODE TABLE
        # =====================
        st.subheader("Node Intelligence")

        nodes = df.groupby("NODE_ID").agg({
            "LIC_RAW": "nunique",
            "usd_amount": "sum"
        }).reset_index()

        nodes.columns = ["Node", "Licenses", "Total Earned"]

        st.dataframe(nodes, use_container_width=True)

else:

    st.info("Paste your Unity JWT token to continue.")
