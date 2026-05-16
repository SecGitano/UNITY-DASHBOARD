import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# =========================
# CONFIG
# =========================
API_URL_BAL = "https://api.unityedge.io/rest/v1/rpc/rewards_get_balance"
API_URL_HIS = "https://api.unityedge.io/rest/v1/rpc/rewards_get_allocations"
API_KEY = "sb_publishable_yKqi0fu5vV6G4ryUIMJuzw_NCoFEl1c"

st.set_page_config(
    page_title="Unity Analytics // Hando Core",
    layout="wide",
    page_icon="🌙"
)


# =========================
# DARK THEME
# =========================
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
    font-weight:700 !important;
}

[data-testid="stSidebar"]{
    background:#020617 !important;
    border-right:1px solid #334155;
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

[data-testid="stMetricValue"]{
    color:#f8fafc !important;
}

[data-testid="stMetricLabel"]{
    color:#94a3b8 !important;
}

.hando-card{
    background:#1e293b;
    border:1px solid #334155;
    border-radius:12px;
    padding:24px;
    margin-bottom:20px;
}

.status-grid{
    display:grid;
    grid-template-columns:repeat(auto-fill,minmax(45px,1fr));
    gap:8px;
    margin:15px 0;
}

.status-box{
    padding:10px 0;
    text-align:center;
    border-radius:6px;
    font-weight:600;
    font-size:.75em;
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


# =========================
# HELPERS
# =========================
def format_id(id_val):
    s = str(id_val)
    return f"{s[:4]}...{s[-4:]}" if len(s) > 10 else s


def parse_balance(data):
    try:
        if isinstance(data, (int, float)):
            return float(data)

        if isinstance(data, list) and len(data):

            item = data[0]

            if isinstance(item, (int, float)):
                return float(item)

            if isinstance(item, dict):
                return float(
                    next(iter(item.values()))
                )

        return 0.0

    except:
        return 0.0


def apply_chart_style(fig):

    fig.update_layout(
        paper_bgcolor="#1e293b",
        plot_bgcolor="#1e293b",
        font_family="Inter",
        font_color="#cbd5e1",
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


# =========================
# DATA ENGINE
# =========================
@st.cache_data(ttl=600, show_spinner=False)
def deep_sync(token):

    token = (
        token
        .strip()
        .replace("Bearer ", "")
    )

    headers = {
        "apikey": API_KEY,
        "authorization": f"Bearer {token}",
        "content-type": "application/json"
    }

    try:

        # -------------------
        # BALANCE
        # -------------------
        r_bal = requests.post(
            API_URL_BAL,
            headers=headers,
            json={},
            timeout=10
        )

        balance = (
            parse_balance(
                r_bal.json()
            ) / 1_000_000
        )

        # -------------------
        # HISTORY
        # -------------------
        all_rows = []

        skip = 0
        batch = 1000

        sync_box = st.empty()

        while True:

            sync_box.info(
                f"Syncing packet {skip}"
            )

            r = requests.post(
                API_URL_HIS,
                headers=headers,
                json={
                    "skip": skip,
                    "take": batch
                },
                timeout=15
            )

            if r.status_code != 200:
                break

            rows = r.json()

            if not rows:
                break

            all_rows.extend(rows)

            if len(rows) < batch:
                break

            skip += batch

        sync_box.empty()

        if not all_rows:
            return None, balance, "No history"

        df = pd.DataFrame(
            all_rows
        )

        # -------------------
        # COLUMN DETECTION
        # -------------------
        d_col = next(
            (
                c for c in df.columns
                if "time" in c.lower()
                or "created" in c.lower()
            ),
            None
        )

        a_col = next(
            (
                c for c in df.columns
                if "amount" in c.lower()
                or "reward" in c.lower()
            ),
            None
        )

        node_col = next(
            (
                c for c in df.columns
                if "node" in c.lower()
            ),
            None
        )

        lic_col = next(
            (
                c for c in df.columns
                if "license" in c.lower()
            ),
            None
        )

        if not all(
            [d_col, a_col, node_col, lic_col]
        ):
            raise Exception(
                f"Bad schema: {list(df.columns)}"
            )

        # -------------------
        # CLEAN DATA
        # -------------------
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

        return df, balance, None

    except Exception as e:

        return None, 0, str(e)


# =========================
# SIDEBAR
# =========================
with st.sidebar:

    st.markdown("## Hando.")

    raw_input = st.text_area(
        "Bearer Token",
        height=160
    )

    if st.button(
        "REFRESH",
        use_container_width=True
    ):
        st.cache_data.clear()
        st.rerun()


# =========================
# MAIN
# =========================
st.title("Analytics Overview")

if raw_input:

    df, balance, err = (
        deep_sync(raw_input)
    )

    if df is not None:

        now = datetime.now()

        today = now.date()

        yesterday = (
            today - timedelta(days=1)
        )

        start_7d = (
            today - timedelta(days=7)
        )

        revenue_7d = df[
            df["date_only"] >= start_7d
        ]["usd_amount"].sum()

        revenue_yesterday = df[
            df["date_only"] == yesterday
        ]["usd_amount"].sum()

        avg_daily = (
            revenue_7d / 7
        )

        # KPIs
        m1, m2, m3, m4 = (
            st.columns(4)
        )

        m1.metric(
            "Wallet",
            f"${balance:,.2f}"
        )

        m2.metric(
            "7D Revenue",
            f"${revenue_7d:,.2f}"
        )

        m3.metric(
            "Yesterday",
            f"${revenue_yesterday:,.4f}"
        )

        m4.metric(
            "Projected Month",
            f"${avg_daily*30:,.2f}"
        )

        st.markdown("")

        # =====================
        # ROW
        # =====================
        c1, c2 = st.columns(2)

        # Heartbeat
        with c1:

            st.markdown(
                '<div class="hando-card">',
                unsafe_allow_html=True
            )

            st.subheader(
                "Node Heartbeat"
            )

            payouts = (
                df.groupby(
                    "LIC_RAW"
                )["timestamp"]
                .max()
                .to_dict()
            )

            html = (
                '<div class="status-grid">'
            )

            licenses = sorted(
                df["LIC_RAW"]
                .unique()
            )

            for i, lic in enumerate(
                licenses,
                1
            ):

                last = payouts.get(
                    lic
                )

                if pd.isna(last):
                    cls = "bg-red"

                else:

                    hrs = (
                        now-last
                    ).total_seconds()/3600

                    if hrs <= 48:
                        cls = "bg-green"
                    elif hrs <= 96:
                        cls = "bg-yellow"
                    else:
                        cls = "bg-red"

                html += (
                    f'<div class="status-box {cls}">#{i}</div>'
                )

            html += "</div>"

            st.markdown(
                html,
                unsafe_allow_html=True
            )

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )

        # Revenue Chart
        with c2:

            st.markdown(
                '<div class="hando-card">',
                unsafe_allow_html=True
            )

            st.subheader(
                "Revenue Stream"
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
                apply_chart_style(fig),
                use_container_width=True
            )

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )

        # =====================
        # NODE TABLE
        # =====================
        st.subheader(
            "Node Intelligence"
        )

        node_stats = (
            df.groupby("NODE_ID")
            .agg({
                "LIC_RAW":
                    lambda x:
                    sorted(set(x)),
                "usd_amount":
                    "sum"
            })
            .reset_index()
        )

        node_stats.columns = [
            "Node ID",
            "Licenses",
            "Total Earned"
        ]

        node_stats[
            "License Count"
        ] = (
            node_stats[
                "Licenses"
            ]
            .apply(len)
        )

        node_stats[
            "Licenses"
        ] = (
            node_stats[
                "Licenses"
            ]
            .apply(
                lambda x:
                "\n".join(
                    format_id(v)
                    for v in x
                )
            )
        )

        node_stats = node_stats[
            [
                "Node ID",
                "License Count",
                "Licenses",
                "Total Earned"
            ]
        ]

        st.dataframe(
            node_stats.sort_values(
                "Total Earned",
                ascending=False
            ),
            column_config={
                "Total Earned":
                    st.column_config.NumberColumn(
                        format="$ %.4f"
                    )
            },
            hide_index=True,
            use_container_width=True
        )

    else:

        st.error(
            f"Sync failed: {err}"
        )

else:

    st.info(
        "Paste your Bearer token in the sidebar."
    )
