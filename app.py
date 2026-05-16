st.subheader("Node Intelligence")

node_stats = (
    df.groupby("NODE_ID")
    .agg({
        "LIC_RAW": lambda x: list(sorted(set(x))),
        "usd_amount": "sum"
    })
    .reset_index()
)

node_stats.columns = [
    "Node ID",
    "Licenses",
    "Total Earned"
]

node_stats["License Count"] = (
    node_stats["Licenses"]
    .apply(len)
)

node_stats["Licenses"] = (
    node_stats["Licenses"]
    .apply(
        lambda x: ", ".join(
            [format_id(v) for v in x]
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
