import streamlit as st
import variables as var

import pandas as pd
import plotly.graph_objects as go




def sankey(sankey_df, numb_of_engagements):
    title = "{} Total Engagements".format(numb_of_engagements)

    required = {"Source", "Target", "Value"}
    missing = required - set(sankey_df.columns)
    if missing:
        raise ValueError(f"sankey_df missing columns: {sorted(missing)}")

    df = sankey_df.copy()
    df["Source"] = df["Source"].astype(str)
    df["Target"] = df["Target"].astype(str)
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce").fillna(0.0)

    df = df[df["Value"] > 0]

    labels = pd.Index(pd.concat([df["Source"], df["Target"]]).unique())
    label_to_idx = {label: i for i, label in enumerate(labels)}

    df["s_idx"] = df["Source"].map(label_to_idx)
    df["t_idx"] = df["Target"].map(label_to_idx)

    # totals
    outflow = df.groupby("s_idx")["Value"].sum()
    inflow = df.groupby("t_idx")["Value"].sum()

    # node "value" = max(inflow, outflow) (this fixes your 2/3 = 66.7% case)
    node_value = {
        i: float(max(inflow.get(i, 0.0), outflow.get(i, 0.0)))
        for i in range(len(labels))
    }

    def pct_of_prev(v, prev_idx):
        denom = node_value.get(prev_idx, 0.0)
        return (float(v) / denom) if denom else 0.0

    def left_html(s):
        return f"<span style='display:block;text-align:left;'>{s}</span>"

    # ---- link hover: value + % of previous (source node total) ----
    link_custom = []
    for s_i, t_i, v in zip(df["s_idx"], df["t_idx"], df["Value"]):
        s_label = labels[int(s_i)]
        t_label = labels[int(t_i)]
        pct = pct_of_prev(v, int(s_i))
        txt = f"{s_label} → {t_label}<br>{int(v)}<br>{pct:.1%} of {s_label}"
        link_custom.append(left_html(txt))

    # ---- node hover: total + % of each immediate parent ----
    incoming = df.groupby(["t_idx", "s_idx"])["Value"].sum().reset_index()
    node_custom = [""] * len(labels)

    for t_i in range(len(labels)):
        total = node_value.get(t_i, 0.0)
        if total == 0:
            node_custom[t_i] = left_html("0")
            continue

        rows = incoming[incoming["t_idx"] == t_i]
        if rows.empty:
            node_custom[t_i] = left_html(f"Total: {int(total)}")
            continue

        lines = [f"Total: {int(total)}"]
        for _, r in rows.iterrows():
            s_i = int(r["s_idx"])
            v = float(r["Value"])
            pct = pct_of_prev(v, s_i)
            lines.append(f"{pct:.1%} of {labels[s_i]}")

        node_custom[t_i] = left_html("<br>".join(lines))

    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="snap",
                node=dict(
                    label=labels.tolist(),
                    pad=18,
                    thickness=16,
                    customdata=node_custom,
                    hovertemplate="%{customdata}<extra></extra>",
                ),
                link=dict(
                    source=df["s_idx"].tolist(),
                    target=df["t_idx"].tolist(),
                    value=df["Value"].astype(float).tolist(),
                    customdata=link_custom,
                    hovertemplate="%{customdata}<extra></extra>",
                ),
            )
        ]
    )

    fig.update_layout(title_text=title, height=520, margin=dict(l=10, r=10, t=50, b=10))
    return fig



def radial(data, day_col="day_of_week", rate_col="smoothed_rate", title="Score by day"):
    df = data[[day_col, rate_col]].copy()

    # preserve given order
    theta = df[day_col].astype(str).tolist()
    r = df[rate_col].tolist()

    # close the loop
    theta += [theta[0]]
    r += [r[0]]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=r,
        theta=theta,
        mode="lines+markers",
        line=dict(width=3),
        marker=dict(size=7),
        hovertemplate="<b>%{theta}</b><br>Score: %{r:.1f}<extra></extra>",
    ))

    fig.update_layout(
        polar=dict(
            angularaxis=dict(
                rotation=90,
                direction="clockwise",
                linecolor="#6B7280",
                gridcolor="rgba(0,0,0,0.15)",
            ),
            radialaxis=dict(
                tickfont=dict(color="#6B7280"),   # numbers
                gridcolor="rgba(0,0,0,0.15)",
                linecolor="#6B7280",
            ),
        ),
    )

    
    return fig






