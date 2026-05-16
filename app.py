import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

from streamlit_wallet_connect import wallet_connect
from supabase import create_client


# ==================================
# CONFIG
# ==================================
API_URL_BAL = "https://api.unityedge.io/rest/v1/rpc/rewards_get_balance"
API_URL_HIS = "https://api.unityedge.io/rest/v1/rpc/rewards_get_allocations"

SUPABASE_URL = (
    "https://vtllpagtmncbkywsqccd.supabase.co"
)

SUPABASE_KEY = (
    "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c"
)

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


st.set_page_config(
    page_title="Unity Analytics",
    layout="wide",
    page_icon="🌙"
)


# ==================================
# DARK THEME
# ==================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

.stApp{
    background:#0f172a;
    color:#e2e8f0;
    font-family:'Inter',sans-serif;
}

h1,h2,h3{
    color:#f8fafc !important;
}

[data-testid="stSidebar"]{
    background:#020617 !important;
}

[data-testid="stSidebar"] *{
    color:#f8fafc !important;
}

[data-testid="stMetric"]{
    background:#1e293b;
    border:1px solid #334155;
    border-radius:12px;
    padding:20px !important;
}

.status-grid{
    display:grid;
    grid-template-columns:repeat(auto-fill,minmax(45px,1fr));
    gap:8px;
}

.status-box{
    padding:10px 0;
    text-align:center;
    border-radius:6px;
    font-size:.75em;
    font-weight:600;
}

.bg-green{
    background:#14532d;
    color:#bbf7d0;
}

.bg-yellow{
    background:#713f12;
    color:#fde68a;
}

.bg-red{
    background:#7f1d1d;
    color:#fecaca;
}
</style>
""", unsafe_allow_html=True)


# ==================================
# HELPERS
# ==================================
def format_id(v):

    s = str(v)

    if len(s) <= 10:
        return s

    return f"{s[:4]}...{s[-4:]}"


def parse_balance_and_licenses(data):

    balance = 0
    licenses = []

    try:

        if isinstance(data, list):

            for item in data:

                if not isinstance(
                    item,
                    dict
                ):
                    continue

                for k, v in item.items():

                    if isinstance(
                        v,
                        (
                            int,
                            float
                        )
                    ):
                        balance = float(v)

                    if "license" in k.lower():

                        if isinstance(
                            v,
                            list
                        ):
                            licenses.extend(v)

                        else:
                            licenses.append(v)

        elif isinstance(
            data,
            dict
        ):

            for k, v in data.items():

                if isinstance(
                    v,
                    (
                        int,
                        float
                    )
                ):
                    balance = float(v)

                if "license" in k.lower():

                    if isinstance(
                        v,
                        list
                    ):
                        licenses.extend(v)

                    else:
                        licenses.append(v)

        licenses = list(
            set(
                str(x)
                for x in licenses
                if x
            )
        )

        return (
            balance,
            licenses
        )

    except:

        return (
            0,
            []
        )


def chart_style(fig):

    fig.update_layout(
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        font_color="#cbd5e1",
        font_family="Inter",
        xaxis=dict(
            showgrid=True,
            gridcolor="#334155"
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#334155"
        )
    )

    return fig


# ==================================
# AUTH
# ==================================
def unity_wallet_login():

    wallet = wallet_connect(
        label="🦊 Connect Wallet"
    )

    if not wallet:
        return None

    auth = (
        supabase
        .auth
        .sign_in_with_web3({
            "chain": "ethereum",
            "statement":
                "Login to Hando Analytics"
        })
    )

    if not auth.session:
        return None

    return (
        auth
        .session
        .access_token
    )


# ==================================
# DATA ENGINE
# ==================================
@st.cache_data(
    ttl=600
)
def deep_sync(token):

    headers = {
        "apikey": SUPABASE_KEY,
        "authorization":
            f"Bearer {token}",
        "content-type":
            "application/json"
    }

    try:

        r_bal = requests.post(
            API_URL_BAL,
            headers=headers,
            json={}
        )

        raw_balance, all_licenses = (
            parse_balance_and_licenses(
                r_bal.json()
            )
        )

        balance = (
            raw_balance / 1_000_000
        )

        rows = []

        skip = 0

        while True:

            r = requests.post(
                API_URL_HIS,
                headers=headers,
                json={
                    "skip": skip,
                    "take": 1000
                }
            )

            packet = r.json()

            if not packet:
                break

            rows.extend(packet)

            if len(packet) < 1000:
                break

            skip += 1000

        if not rows:

            return (
                None,
                0,
                [],
                "No data"
            )

        df = pd.DataFrame(
            rows
        )

        d_col = next(
            c for c in df.columns
            if "time" in c.lower()
            or "created" in c.lower()
        )

        a_col = next(
            c for c in df.columns
            if "amount" in c.lower()
            or "reward" in c.lower()
        )

        node_col = next(
            c for c in df.columns
            if "node" in c.lower()
        )

        lic_col = next(
            c for c in df.columns
            if "license" in c.lower()
        )

        df["timestamp"] = (
            pd.to_datetime(
                df[d_col],
                utc=True,
                format="mixed",
                errors="coerce"
            )
            .dt.tz_localize(None)
        )

        df = df.dropna(
            subset=["timestamp"]
        )

        df["usd_amount"] = (
            pd.to_numeric(
                df[a_col],
                errors="coerce"
            )
            .fillna(0)
            / 1_000_000
        )

        df["date_only"] = (
            df["timestamp"]
            .dt.date
        )

        df["NODE_RAW"] = (
            df[node_col]
        )

        df["LIC_RAW"] = (
            df[lic_col]
        )

        df["NODE_ID"] = (
            df["NODE_RAW"]
            .apply(format_id)
        )

        return (
            df,
            balance,
            all_licenses,
            None
        )

    except Exception as e:

        return (
            None,
            0,
            [],
            str(e)
        )


# ==================================
# SIDEBAR
# ==================================
with st.sidebar:

    st.markdown(
        "## Hando."
    )

    if "unity_token" not in st.session_state:

        token = (
            unity_wallet_login()
        )

        if token:

            st.session_state[
                "unity_token"
            ] = token

            st.rerun()

    else:

        st.success(
            "Wallet Connected"
        )

        if st.button(
            "Disconnect",
            use_container_width=True
        ):

            st.session_state.clear()

            st.rerun()


# ==================================
# MAIN
# ==================================
st.title(
    "Analytics Overview"
)

if "unity_token" in st.session_state:

    df, balance, all_licenses, err = (
        deep_sync(
            st.session_state[
                "unity_token"
            ]
        )
    )

    if df is None:

        st.error(
            err
        )

    else:

        now = datetime.now()

        week = (
            now.date()
            - timedelta(days=7)
        )

        yesterday = (
            now.date()
            - timedelta(days=1)
        )

        rev7 = df[
            df["date_only"] >= week
        ]["usd_amount"].sum()

        rev1 = df[
            df["date_only"] == yesterday
        ]["usd_amount"].sum()

        m1, m2, m3 = (
            st.columns(3)
        )

        m1.metric(
            "Wallet",
            f"${balance:,.2f}"
        )

        m2.metric(
            "7D",
            f"${rev7:,.2f}"
        )

        m3.metric(
            "Yesterday",
            f"${rev1:,.4f}"
        )

        # licenses
        active = set(
            str(x)
            for x in df[
                "LIC_RAW"
            ].unique()
        )

        known = set(
            str(x)
            for x in all_licenses
        )

        inactive = (
            known - active
        )

        st.subheader(
            "License Status"
        )

        l1, l2 = st.columns(2)

        l1.metric(
            "Active",
            len(active)
        )

        l2.metric(
            "Inactive",
            len(inactive)
        )

        # revenue chart
        st.subheader(
            "Revenue"
        )

        daily = (
            df.groupby(
                "date_only"
            )["usd_amount"]
            .sum()
            .reset_index()
        )

        fig = px.area(
            daily,
            x="date_only",
            y="usd_amount"
        )

        st.plotly_chart(
            chart_style(fig),
            use_container_width=True
        )

        # node map
        st.subheader(
            "Node Intelligence"
        )

        nodes = (
            df.groupby(
                "NODE_ID"
            )
            .agg({
                "LIC_RAW":
                    lambda x:
                    "\n".join(
                        sorted(
                            set(
                                format_id(v)
                                for v in x
                            )
                        )
                    ),
                "usd_amount":
                    "sum"
            })
            .reset_index()
        )

        nodes.columns = [
            "Node",
            "Licenses",
            "Total"
        ]

        st.dataframe(
            nodes,
            hide_index=True,
            use_container_width=True
        )

else:

    st.info(
        "Connect your wallet."
    )
