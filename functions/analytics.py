import streamlit as st
import variables as var

import pandas as pd
import plotly.graph_objects as go
import numpy as np
import plotly.express as px


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



def radial(data, day_col="day_of_week", rate_col="smoothed_rate"):
    df = data[[day_col, rate_col]].copy()

    theta = df[day_col].astype(str).tolist()
    r = df[rate_col].tolist()

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
                tickfont=dict(color="#6B7280"),
                gridcolor="rgba(0,0,0,0.15)",
                linecolor="#6B7280",
            ),
        ),
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
    )

    return fig



def horizontal_boxplot(numeric_col, title=None, color="#636EFA", trace_name="Minutes"):


    x = np.asarray(numeric_col, dtype=float)
    x = x[np.isfinite(x)]

    fig = go.Figure(
        go.Box(
            x=x,
            orientation="h",
            boxpoints="outliers",
            name=trace_name,   # <- shows "Minutes" instead of trace0
            showlegend=False,
            marker_color=color,
        )
    )

    fig.update_layout(title=title, dragmode="zoom")
    fig.update_yaxes(fixedrange=True)
    fig.update_xaxes(hoverformat=",.0f")

    return fig






_TIME_BINS = [
    (0, 4,  "12 - 4am"),
    (4, 8,  "4 - 8am"),
    (8, 12, "8am - 12pm"),
    (12, 16,"12 - 4pm"),
    (16, 20,"4 - 8pm"),
    (20, 24,"8pm - 12am"),
]

def scatter_plot(
    df,
    x_key,
    y_col,
    first_ts_col,
    title=None,
    color="#636EFA",
    jitter=0.18,
):

    DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    TIME_BIN_ORDER = [label for _, _, label in _TIME_BINS]
    DAYTIME_ORDER = [f"{d} • {t}" for d in DAY_ORDER for t in TIME_BIN_ORDER]

    def _time_bin_label(ts: pd.Series) -> pd.Series:
        h = ts.dt.hour
        out = pd.Series(index=ts.index, dtype="object")
        for start, end, label in _TIME_BINS:
            out[(h >= start) & (h < end)] = label
        return out

    ts = pd.to_datetime(df[first_ts_col], errors="coerce")

    # Build X
    if x_key == "First Message: Time of Day":
        x_series = _time_bin_label(ts)
        cat_order = TIME_BIN_ORDER
        x_title = x_key
        x_is_cat = True

    elif x_key == "First Message: Day of Week":
        x_series = ts.dt.day_name()
        cat_order = DAY_ORDER
        x_title = x_key
        x_is_cat = True

    elif x_key == "First Message: Daytime":
        x_series = ts.dt.day_name().astype(str) + " • " + _time_bin_label(ts).astype(str)
        cat_order = DAYTIME_ORDER
        x_title = x_key
        x_is_cat = True

    else:
        x_series = pd.to_numeric(df[x_key], errors="coerce")
        x_title = str(x_key)
        x_is_cat = False

    y_series = pd.to_numeric(df[y_col], errors="coerce")

    if x_is_cat:
        mask = x_series.notna() & y_series.notna()
        x_series = x_series[mask].astype(str)
        y_series = y_series[mask]

        x_cat = pd.Categorical(x_series, categories=cat_order, ordered=True)
        codes = x_cat.codes.astype(float)

        # drop anything not in categories (-1 code)
        ok = codes >= 0
        codes = codes[ok]
        y_vals = y_series.iloc[np.where(ok)[0]].astype(float).round().astype(int)

        rng = np.random.default_rng(42)
        x_plot = codes + rng.uniform(-jitter, jitter, size=len(codes))

        fig = go.Figure(
            go.Scatter(
                x=x_plot,
                y=y_vals,
                mode="markers",
                marker=dict(color=color),
                customdata=np.array(x_cat[ok].astype(str)),
                hovertemplate=(
                    f"{x_title}: %{{customdata}}<br>"
                    f"{y_col}: %{{y:,.0f}}"
                    "<extra></extra>"
                ),
            )
        )

        fig.update_xaxes(
            title=x_title,
            tickmode="array",
            tickvals=np.arange(len(cat_order)),
            ticktext=cat_order,
            zeroline=False,
        )

    else:
        mask = x_series.notna() & y_series.notna()
        x_vals = x_series[mask].astype(float).round().astype(int)
        y_vals = y_series[mask].astype(float).round().astype(int)

        fig = go.Figure(
            go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="markers",
                marker=dict(color=color),
                hovertemplate=(
                    f"{x_title}: %{{x:,.0f}}<br>"
                    f"{y_col}: %{{y:,.0f}}"
                    "<extra></extra>"
                ),
            )
        )

        fig.update_xaxes(title=x_title, hoverformat=",.0f")

    fig.update_yaxes(title=str(y_col), hoverformat=",.0f")
    fig.update_layout(title=title)

    return fig



def stacked_events_bar_fig(events_df, ts_col=None):

    df = events_df.copy()

    # infer / validate timestamp col
    if ts_col is None or ts_col not in df.columns:
        # prefer your two canonical names first
        for c in ["Event Timestamp", "Like Timestamp"]:
            if c in df.columns:
                ts_col = c
                break
        else:
            candidates = [c for c in df.columns if "timestamp" in c.lower()]
            ts_col = candidates[0] if candidates else df.columns[0]

    df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
    if pd.api.types.is_datetime64tz_dtype(df[ts_col]):
        df[ts_col] = df[ts_col].dt.tz_convert(None)

    df = df.dropna(subset=[ts_col, "event"])
    if df.empty:
        return None, None
        
    tmin = df[ts_col].min()
    tmax = df[ts_col].max()
    span = tmax - tmin

    def ge_offset(dt_min, dt_max, offset):
        return dt_max >= (dt_min + offset)

    one_day = pd.Timedelta(days=1)

    # -------- group-by selector (dynamic options) --------
    if span < one_day:
        bucket = "All"
    else:
        opts = ["Day"]
        if span >= pd.Timedelta(days=7):
            opts = ["Week"] + opts
        if ge_offset(tmin, tmax, pd.DateOffset(months=1)):
            opts = ["Month"] + opts
        if ge_offset(tmin, tmax, pd.DateOffset(months=3)):
            opts = ["Quarter"] + opts
        if ge_offset(tmin, tmax, pd.DateOffset(years=1)):
            opts = ["Year"] + opts

        bucket = st.selectbox("Group by", opts, index=0)

    # -------- bucketing + pretty hover labels --------
    if bucket == "All":
        df["_bucket_dt"] = pd.Timestamp("1970-01-01")
        df["_bucket_label"] = "All time"
        df["_hover_label"] = "All time"

    elif bucket == "Year":
        df["_bucket_dt"] = df[ts_col].dt.to_period("Y").dt.start_time
        df["_bucket_label"] = df["_bucket_dt"].dt.strftime("%Y")
        df["_hover_label"] = df["_bucket_label"]

    elif bucket == "Quarter":
        p = df[ts_col].dt.to_period("Q")
        df["_bucket_dt"] = p.dt.start_time
        df["_bucket_label"] = p.astype(str)               # 2026Q4
        df["_hover_label"] = df["_bucket_label"].str.replace("Q", " Q", regex=False)  # 2026 Q4

    elif bucket == "Month":
        df["_bucket_dt"] = df[ts_col].dt.to_period("M").dt.start_time
        df["_bucket_label"] = df["_bucket_dt"].dt.strftime("%Y-%m")   # stable x ordering
        df["_hover_label"] = df["_bucket_dt"].dt.strftime("%b %Y")    # Jan 2026

    elif bucket == "Week":
        df["_bucket_dt"] = df[ts_col].dt.to_period("W-MON").dt.start_time
        week_end = df["_bucket_dt"] + pd.Timedelta(days=6)
        df["_bucket_label"] = df["_bucket_dt"].dt.strftime("%Y-%m-%d")
        df["_hover_label"] = (
            df["_bucket_dt"].dt.strftime("%d.%m.%Y") + " – " + week_end.dt.strftime("%d.%m.%Y")
        )

    else:  # Day
        df["_bucket_dt"] = df[ts_col].dt.floor("D")
        df["_bucket_label"] = df["_bucket_dt"].dt.strftime("%Y-%m-%d")
        df["_hover_label"] = df["_bucket_dt"].dt.strftime("%d.%m.%Y")

    # -------- aggregate --------
    agg = (
        df.groupby(["_bucket_label", "_hover_label", "event"], as_index=False)
          .size()
          .rename(columns={"size": "count"})
    )

    # chronological order
    sort_key = (
        df.drop_duplicates("_bucket_label")[["_bucket_label", "_bucket_dt"]]
          .sort_values("_bucket_dt")
    )
    agg = agg.merge(sort_key, on="_bucket_label", how="left").sort_values("_bucket_dt")

    # stack + legend order (bottom -> top)
    order = [
        "Like sent",
        "Comment",
        "Like received",
        "Match",
        "Conversation",
        "We met",
        "My type",
        "Block",
    ]
    extras = [e for e in agg["event"].unique().tolist() if e not in order]
    category_order = order + sorted(extras)

    fig = px.bar(
        agg,
        x="_bucket_label",
        y="count",
        color="event",
        barmode="stack",
        title=title,
        category_orders={"event": category_order},
        custom_data=["_hover_label", "event", "count"],
    )

    # clean hover
    fig.update_traces(
        hovertemplate="%{customdata[0]}<br>%{customdata[1]}: %{customdata[2]}<extra></extra>"
    )

    # remove legend title, keep legend ordered
    fig.update_layout(
        legend_title_text="",
        xaxis_title=None,
        yaxis_title=None,
    )

    fig.update_layout(legend_traceorder="reversed")

    fig.update_xaxes(type="category", tickangle=0)
            
    # zoom only on X (lock Y)
    fig.update_yaxes(fixedrange=True)
    
    # -------- partial bucket warning --------
    warning = None
    if bucket != "All":
        tmin0 = pd.Timestamp(tmin).tz_localize(None) if getattr(tmin, "tzinfo", None) else pd.Timestamp(tmin)
        tmax0 = pd.Timestamp(tmax).tz_localize(None) if getattr(tmax, "tzinfo", None) else pd.Timestamp(tmax)

        def bounds(dt, mode):
            dt = pd.Timestamp(dt).tz_localize(None) if getattr(dt, "tzinfo", None) else pd.Timestamp(dt)
            if mode == "Year":
                start = pd.Timestamp(dt.year, 1, 1)
                end = pd.Timestamp(dt.year + 1, 1, 1)
            elif mode == "Quarter":
                q = ((dt.month - 1) // 3) * 3 + 1
                start = pd.Timestamp(dt.year, q, 1)
                end = start + pd.DateOffset(months=3)
            elif mode == "Month":
                start = pd.Timestamp(dt.year, dt.month, 1)
                end = start + pd.DateOffset(months=1)
            elif mode == "Week":
                start = dt.normalize() - pd.Timedelta(days=dt.weekday())
                end = start + pd.Timedelta(days=7)
            else:  # Day
                start = dt.normalize()
                end = start + pd.Timedelta(days=1)
            return start, end

        first_bucket_start, _ = bounds(tmin0, bucket)
        _, last_bucket_end = bounds(tmax0, bucket)

        if (tmin0 > first_bucket_start) or (tmax0 < last_bucket_end):
            warning = "⚠️ Time buckets may be partial at the edges (data doesn’t cover full calendar buckets)."

    return fig, warning


