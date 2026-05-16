import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_javascript import st_javascript


# ==================================
# CONFIG
# ==================================
API_URL_BAL = "https://api.unityedge.io/rest/v1/rpc/rewards_get_balance"
API_URL_HIS = "https://api.unityedge.io/rest/v1/rpc/rewards_get_allocations"
API_KEY = "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c"

SUPABASE_URL = "https://vtllpagtmncbkywsqccd.supabase.co"
SUPABASE_ANON = API_KEY


st.set_page_config(
    page_title="Unity Analytics",
    layout="wide",
    page_icon="🌙"
)


# ==================================
# DARK MODE
# ==================================
st.markdown("""
<style>
.stApp { background:#0f172a; color:#e2e8f0; }

h1,h2,h3 { color:#f8fafc !important; }

[data-testid="stSidebar"]{
    background:#020617;
}

[data-testid="stMetric"]{
    background:#1e293b;
    border-radius:12px;
    border:1px solid #334155;
    padding:18px;
}

.card {
    background:#1e293b;
    padding:20px;
    border-radius:12px;
    border:1px solid #334155;
}
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
            return float(list(data[0].values())[0])
        return 0.0
    except:
        return 0.0


# ==================================
# SIWE LOGIN (FULL AUTO)
# ==================================
def siwe_login():

    auth = st_javascript(f"""
    async () => {{

        if (!window.ethereum) {{
            return {{error: "no_wallet"}};
        }}

        const accounts = await window.ethereum.request({{
            method: "eth_requestAccounts"
        }});

        const address = accounts[0];

        const nonceRes = await fetch(
            "{SUPABASE_URL}/auth/v1/otp",
            {{
                method: "POST",
                headers: {{
                    "apikey": "{SUPABASE_ANON}",
                    "Content-Type": "application/json"
                }},
                body: JSON.stringify({{
                    "email": address + "@wallet.local"
                }})
            }}
        );

        const message =
            `Sign in to Unity Analytics\\nWallet: ${{address}}\\nNonce: login`;

        const signature = await window.ethereum.request({{
            method: "personal_sign",
            params: [message, address]
        }});

        return {{
            address,
            signature,
            message
        }};
    }}
    """)

    if not auth:
        return None

    if isinstance(auth, dict) and auth.get("error"):
        return None

    return auth["address"]


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
            return None, 0, None

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
# AUTH FLOW
# ==================================
with st.sidebar:

    st.markdown("## Hando")

    if "wallet" not in st.session_state:

        if st.button("🦊 Connect Wallet", use_container_width=True):

            wallet = siwe_login()

            if wallet:

                st.session_state["wallet"] = wallet
                st.success(f"Connected {wallet[:6]}...{wallet[-4:]}")
                st.rerun()

    else:

        st.success(f"Wallet: {st.session_state['wallet'][:6]}...")

        if st.button("Disconnect"):
            st.session_state.clear()
            st.rerun()


# ==================================
# MAIN
# ==================================
st.title("Analytics Overview")

if "wallet" in st.session_state:

    # For now: wallet acts as identity gate
    token = API_KEY  # Unity backend still authorizes via project key

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

        c1.metric("Wallet Connected", "✔")
        c2.metric("7D Revenue", f"${rev7:,.2f}")
        c3.metric("Yesterday", f"${rev1:,.4f}")

        st.subheader("License Status")
        st.metric("Active Licenses", df["LIC_RAW"].nunique())

        st.subheader("Revenue")

        daily = df.groupby("date_only")["usd_amount"].sum().reset_index()

        st.plotly_chart(
            px.area(daily, x="date_only", y="usd_amount"),
            use_container_width=True
        )

        st.subheader("Node Intelligence")

        nodes = df.groupby("NODE_ID").agg({
            "LIC_RAW": "nunique",
            "usd_amount": "sum"
        }).reset_index()

        nodes.columns = ["Node", "Licenses", "Total"]

        st.dataframe(nodes, use_container_width=True)

else:

    st.info("Click Connect Wallet to begin")
