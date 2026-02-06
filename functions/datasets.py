import pandas as pd
from functions.authentification import supabase
import variables as var
import numpy as np

import streamlit as st

def _dedupe_keep_best(df):
    # priority (best first):
    # we_met True > my_type True > has block_id > has comment_message_id >
    # max conversation_message_count > max conversation_span_minutes >
    # newest match_timestamp > newest like_timestamp > newest first_message_timestamp

    # build sort keys as arrays (no new columns)
    k_we_met = df[var.col_we_met].fillna(False).astype(bool).to_numpy() if var.col_we_met in df.columns else np.zeros(len(df), dtype=bool)
    k_my_type = df[var.col_my_type].fillna(False).astype(bool).to_numpy() if var.col_my_type in df.columns else np.zeros(len(df), dtype=bool)
    k_has_block = df[var.col_block_id].notna().to_numpy() if var.col_block_id in df.columns else np.zeros(len(df), dtype=bool)
    k_has_comment = df[var.col_comment_message_id].notna().to_numpy() if var.col_comment_message_id in df.columns else np.zeros(len(df), dtype=bool)

    k_msg_cnt = df[var.col_conversation_message_count].fillna(0).to_numpy() if var.col_conversation_message_count in df.columns else np.zeros(len(df))
    k_span = df[var.col_conversation_span_minutes].fillna(0).to_numpy() if var.col_conversation_span_minutes in df.columns else np.zeros(len(df))

    def _ts_key(col):
        if col in df.columns:
            s = pd.to_datetime(df[col], errors="coerce")
            return s.view("int64").to_numpy()  # NaT -> very negative
        return np.full(len(df), np.iinfo(np.int64).min, dtype=np.int64)

    k_match_ts = _ts_key(var.col_match_timestamp)
    k_like_ts = _ts_key(var.col_like_timestamp)
    k_first_msg_ts = _ts_key(var.col_first_message_timestamp) if hasattr(var, "col_first_message_timestamp") else _ts_key("first_message_timestamp")

    # lexsort: last key has highest priority -> put lowest priority first
    order = np.lexsort((
        k_first_msg_ts,
        k_like_ts,
        k_match_ts,
        k_span,
        k_msg_cnt,
        k_has_comment,
        k_has_block,
        k_my_type,
        k_we_met,
    ))

    df = df.iloc[order[::-1]].copy()  # best first

    # enforce uniqueness for each ID column (keep best)
    id_cols = [
        var.col_like_id,
        var.col_match_id,
        var.col_comment_message_id,
        var.col_block_id,
    ]

    for c in id_cols:
        if c in df.columns:
            mask = df[c].isna() | ~df[c].duplicated(keep="first")
            df = df.loc[mask]

    return df






def like_events_df(user_id, tz="America/Toronto"):
    likes_df = pd.DataFrame(
        supabase.table(var.table_likes).select("*").eq(var.col_user_id, user_id).execute().data or []
    )
    messages_df = pd.DataFrame(
        supabase.table(var.table_messages).select("*").eq(var.col_user_id, user_id).execute().data or []
    )
    matches_df = pd.DataFrame(
        supabase.table(var.table_matches).select("*").eq(var.col_user_id, user_id).execute().data or []
    )
    blocks_df = pd.DataFrame(
        supabase.table(var.table_blocks).select("*").eq(var.col_user_id, user_id).execute().data or []
    )

    st.write(matches_df)
    # timestamps (parse only; tz handled after concat)
    # for df in [likes_df, messages_df, matches_df, blocks_df]:
    #     for c in df.columns:
    #         if c.endswith("_timestamp"):
    #             s = pd.to_datetime(df[c].astype("string"), errors="coerce", utc=True)
    #             df[c] = s.dt.tz_convert(tz).dt.tz_localize(None).dt.floor("s")

    st.write(matches_df)
    # comments (messages tied to like_id)
    comments = (
        messages_df.dropna(subset=[var.col_like_id])[[var.col_message_id, var.col_like_id]]
        .rename(columns={var.col_message_id: var.col_comment_message_id})
        .drop_duplicates(subset=[var.col_like_id])
    )

    # convo msgs (exclude comments)
    convo_msgs = messages_df[messages_df[var.col_like_id].isna()].copy()

    # convo aggregates
    convo_agg = (
        convo_msgs.groupby(var.col_match_id)
        .agg(**{
            var.col_conversation_message_count: (var.col_message_id, "count"),
            var.col_first_message_timestamp: (var.col_message_timestamp, "min"),
            "last_message_ts": (var.col_message_timestamp, "max"),
        })
        .reset_index()
    )

    convo_agg[var.col_conversation_span_minutes] = (
        (convo_agg["last_message_ts"] - convo_agg[var.col_first_message_timestamp])
        .dt.total_seconds() / 60
    )

    # avg time between messages (minutes)
    avg_gap = (
        convo_msgs
        .sort_values(var.col_message_timestamp)
        .groupby(var.col_match_id)[var.col_message_timestamp]
        .apply(lambda x: x.diff().dt.total_seconds().mean() / 60)
        .reset_index(name=var.col_avg_message_gap)
    )

    convo_agg = convo_agg.merge(avg_gap, on=var.col_match_id, how="left")
    convo_agg = convo_agg.drop(columns=["last_message_ts"])

    # blocks (one per match)
    blocks_agg = (
        blocks_df.dropna(subset=[var.col_match_id])
        .sort_values(var.col_block_timestamp)
        .drop_duplicates(var.col_match_id)
        [[var.col_match_id, var.col_block_id, var.col_block_timestamp]]
    )

    # matches subset
    matches_sub = matches_df[
        [var.col_match_id, var.col_match_timestamp, var.col_we_met, var.col_my_type, var.col_we_met_timestamp]
    ].copy()

    st.write(matches_sub)
    # sent likes
    sent = likes_df.copy()
    sent = sent.merge(comments, on=var.col_like_id, how="left")
    sent = sent.merge(matches_sub, on=var.col_match_id, how="left")
    sent = sent.merge(convo_agg, on=var.col_match_id, how="left")
    sent = sent.merge(blocks_agg, on=var.col_match_id, how="left")

    # received likes
    like_match_ids = set(likes_df[var.col_match_id].dropna().unique()) if var.col_match_id in likes_df.columns else set()
    received_matches = matches_df[~matches_df[var.col_match_id].isin(like_match_ids)].copy()

    received = received_matches.copy()
    received[var.col_like_id] = pd.NA
    received[var.col_like_timestamp] = pd.NaT
    received[var.col_comment_message_id] = pd.NA

    received = received.merge(convo_agg, on=var.col_match_id, how="left")
    received = received.merge(blocks_agg, on=var.col_match_id, how="left")

    # align + concat
    for col in sent.columns:
        if col not in received.columns:
            received[col] = pd.NA
    received = received[sent.columns]

    base_df = pd.concat([sent, received], ignore_index=True)

    # TZ CONVERSION (UTC -> tz, then drop tz info; do upstream once)
    def _to_local_naive(s):
        s = pd.to_datetime(s, errors="coerce")
        if s.dt.tz is None:
            s = s.dt.tz_localize("UTC")
        return s.dt.tz_convert(tz).dt.tz_localize(None)
        
    for c in base_df.columns:
        if c.endswith("_timestamp"):
            base_df[c] = _to_local_naive(base_df[c])

    
    base_df[var.col_like_direction] = base_df[var.col_like_id].isna().map({True: "received", False: "sent"})
    
    base_df[var.col_first_message_delay] = (
        (base_df[var.col_first_message_timestamp] - base_df[var.col_match_timestamp])
        .dt.total_seconds() / 60
    )

    base_df[var.col_like_match_delay] = (
        (base_df[var.col_match_timestamp] - base_df[var.col_like_timestamp])
        .dt.total_seconds() / 60
    )

    base_df = _dedupe_keep_best(base_df)
    return base_df







def sankey_data(data, min_messages=2, min_minutes=5, join_comments_and_likes_sent=False):
    
    df = data.copy()

    is_sent = df[var.col_like_direction].eq("sent")
    is_received = df[var.col_like_direction].eq("received")
    has_comment = df[var.col_comment_message_id].notna()

    comments = df[is_sent & has_comment]
    likes_sent = df[is_sent & ~has_comment]
    likes_received = df[is_received]

    comments_m = comments[comments[var.col_match_id].notna()]
    likes_sent_m = likes_sent[likes_sent[var.col_match_id].notna()]
    likes_received_m = likes_received[likes_received[var.col_match_id].notna()]

    comments_nm = comments[comments[var.col_match_id].isna()]
    likes_sent_nm = likes_sent[likes_sent[var.col_match_id].isna()]
    likes_received_nm = likes_received[likes_received[var.col_match_id].isna()]

    matched = df[df[var.col_match_id].notna()].copy()

    msg_cnt = matched[var.col_conversation_message_count].fillna(0)
    span_min = matched[var.col_conversation_span_minutes].fillna(0)
    is_convo = (msg_cnt >= min_messages) & (span_min >= min_minutes)

    is_we_met = matched[var.col_we_met].fillna(False).astype(bool)
    is_blocked = matched[var.col_block_id].notna()

    we_met_via_convo = matched[is_convo & is_we_met]
    we_met_direct = matched[~is_convo & is_we_met]

    blocks_via_convo = matched[is_convo & is_blocked]
    blocks_direct = matched[~is_convo & is_blocked]

    my_type = matched[is_we_met & matched[var.col_my_type].fillna(False).astype(bool)]

    if join_comments_and_likes_sent:
        start = "Comments & likes sent"
        start_matches = comments_m[var.col_match_id].nunique() + likes_sent_m[var.col_match_id].nunique()
        start_no_match = len(comments_nm) + len(likes_sent_nm)

        flows = [
            (start, "Matches", start_matches),
            (start, "No match", start_no_match),

            ("Likes received", "Matches", likes_received_m[var.col_match_id].nunique()),
            ("Likes received", "No match", len(likes_received_nm)),
        ]
    else:
        flows = [
            ("Comments", "Matches", comments_m[var.col_match_id].nunique()),
            ("Comments", "No match", len(comments_nm)),

            ("Likes sent", "Matches", likes_sent_m[var.col_match_id].nunique()),
            ("Likes sent", "No match", len(likes_sent_nm)),

            ("Likes received", "Matches", likes_received_m[var.col_match_id].nunique()),
            ("Likes received", "No match", len(likes_received_nm)),
        ]

    flows += [
        ("Matches", "Conversations", matched[is_convo][var.col_match_id].nunique()),

        ("Matches", "We met", we_met_direct[var.col_match_id].nunique()),
        ("Conversations", "We met", we_met_via_convo[var.col_match_id].nunique()),

        ("Matches", "Blocks", blocks_direct[var.col_match_id].nunique()),
        ("Conversations", "Blocks", blocks_via_convo[var.col_match_id].nunique()),

        ("We met", "My type", my_type[var.col_match_id].nunique()),
    ]

    return (
        pd.DataFrame(flows, columns=["Source", "Target", "Value"])
        .groupby(["Source", "Target"], as_index=False)["Value"].sum()
        .query("Value > 0")
    )









_TIME_BINS = [
    (0, 4,  "12 - 4am"),
    (4, 8,  "4 - 8am"),
    (8, 12, "8am - 12pm"),
    (12, 16,"12 - 4pm"),
    (16, 20,"4 - 8pm"),
    (20, 24,"8pm - 12am"),
]
_TIME_ORDER = [label for _, _, label in _TIME_BINS]
_DOW_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

def _time_bucket_from_dt(dt_series):
    hrs = dt_series.dt.hour
    out = pd.Series(pd.NA, index=dt_series.index, dtype="object")
    for start, end, label in _TIME_BINS:
        out[(hrs >= start) & (hrs < end)] = label
    return pd.Categorical(out, categories=_TIME_ORDER, ordered=True)

def _dow_from_dt(dt_series):
    return pd.Categorical(dt_series.dt.day_name(), categories=_DOW_ORDER, ordered=True)

def likes_matches_agg(data, by="time", m=100):
    """
    by: "time" | "day" | "day_time"
    Returns counts + raw_rate + smoothed_rate for sent likes only.
    """
    if by not in {"time", "day", "day_time"}:
        raise ValueError('by must be "time", "day", or "day_time"')

    df = data.copy()

    # Only sent likes
    if var.col_like_direction in df.columns:
        df = df[df.like_direction == "sent"].copy()

    # Parse timestamps (assumes already-localized upstream)
    df.like_timestamp  = pd.to_datetime(df.like_timestamp, errors="coerce")
    df.match_timestamp = pd.to_datetime(df.match_timestamp, errors="coerce")

    # Global baseline rate (sent only)
    total_likes = df.like_id.nunique() if var.col_like_id in df.columns else 0
    total_matches = df.match_id.nunique() if var.col_match_id in df.columns else 0
    global_rate = (total_matches / total_likes) if total_likes else 0

    # Group keys for likes
    like_day  = _dow_from_dt(df.like_timestamp)
    like_time = _time_bucket_from_dt(df.like_timestamp)

    # Matches frame + keys
    match_df = df.dropna(subset=[var.col_match_id, "match_timestamp"]).copy()
    match_day  = _dow_from_dt(match_df.match_timestamp)
    match_time = _time_bucket_from_dt(match_df.match_timestamp)

    if by == "time":
        group_order = _TIME_ORDER

        likes = (
            df.groupby(like_time, dropna=False)[var.col_like_id]
              .nunique()
              .reindex(group_order, fill_value=0)
              .rename(var.table_likes)
        )

        matches = (
            match_df.groupby(match_time, dropna=False)[var.col_match_id]
                    .nunique()
                    .reindex(group_order, fill_value=0)
                    .rename(var.json_matches)
        )

        out = pd.concat([likes, matches], axis=1).fillna(0).reset_index()
        out = out.rename(columns={"index": "time_bucket", 0: "time_bucket"})
        out["time_bucket"] = out["time_bucket"].astype(str)

    elif by == "day":
        group_order = _DOW_ORDER

        likes = (
            df.groupby(like_day, dropna=False)[var.col_like_id]
              .nunique()
              .reindex(group_order, fill_value=0)
              .rename(var.table_likes)
        )

        matches = (
            match_df.groupby(match_day, dropna=False)[var.col_match_id]
                    .nunique()
                    .reindex(group_order, fill_value=0)
                    .rename(var.json_matches)
        )

        out = pd.concat([likes, matches], axis=1).fillna(0).reset_index()
        out = out.rename(columns={"index": "day_of_week", 0: "day_of_week"})
        out["day_of_week"] = out["day_of_week"].astype(str)

    else:  # "day_time"
        full_index = pd.MultiIndex.from_product(
            [_DOW_ORDER, _TIME_ORDER],
            names=["day_of_week", "time_bucket"]
        )

        likes = (
            df.groupby([like_day, like_time], dropna=False)[var.col_like_id]
              .nunique()
              .reindex(full_index, fill_value=0)
              .rename(var.table_likes)
        )

        matches = (
            match_df.groupby([match_day, match_time], dropna=False)[var.col_match_id]
                    .nunique()
                    .reindex(full_index, fill_value=0)
                    .rename(var.json_matches)
        )

        out = pd.concat([likes, matches], axis=1).fillna(0).reset_index()
        out["day_of_week"] = pd.Categorical(out.day_of_week, categories=_DOW_ORDER, ordered=True)
        out["time_bucket"] = pd.Categorical(out.time_bucket, categories=_TIME_ORDER, ordered=True)
        out = out.sort_values(["day_of_week", "time_bucket"]).reset_index(drop=True)
        out["day_of_week"] = out["day_of_week"].astype(str)
        out["time_bucket"] = out["time_bucket"].astype(str)

    # Rates
    out[var.table_likes] = out[var.table_likes].astype(int)
    out[var.json_matches] = out[var.json_matches].astype(int)

    out["raw_rate"] = (
        out[var.json_matches] / out[var.table_likes]
    ).replace([float("inf")], 0).fillna(0)

    out["smoothed_rate"] = (
        (out[var.json_matches] + m * global_rate) /
        (out[var.table_likes] + m)
    ).fillna(0).where(out[var.json_matches] > 0, 0)

    out["smoothed_rate"] *= 100

    return out


def likes_matches_aggs(data):
    return {
        "time":     likes_matches_agg(data, by="time", m=m),
        "day":      likes_matches_agg(data, by="day", m=m),
        "day_time": likes_matches_agg(data, by="day_time", m=m),
    }






def events_over_time_df(
    data,
    min_messages=2,
    min_minutes=5,
    join_comments_and_likes_sent=False,
    use_like_timestamp=True,
):

    df = data.copy()

    ts_col_name = "Like Timestamp" if use_like_timestamp else "Event Timestamp"

    # ensure timestamps are datetime
    for c in [
        var.col_like_timestamp,
        var.col_match_timestamp,
        var.col_first_message_timestamp,
        var.col_we_met_timestamp,
        var.col_block_timestamp,
    ]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")

    is_sent = df[var.col_like_direction].eq("sent")
    is_received = df[var.col_like_direction].eq("received")
    has_comment = df[var.col_comment_message_id].notna()

    # -----------------------------
    # Likes / Comments
    # -----------------------------
    base_ts = var.col_like_timestamp if use_like_timestamp else var.col_like_timestamp

    if join_comments_and_likes_sent:
        sent_any = df[is_sent & df[base_ts].notna()]
        likes_events = pd.DataFrame(
            {ts_col_name: sent_any[base_ts], "event": "Comments & likes sent"}
        )
    else:
        comments = df[is_sent & has_comment & df[base_ts].notna()]
        likes_sent = df[is_sent & ~has_comment & df[base_ts].notna()]

        likes_events = pd.concat(
            [
                pd.DataFrame({ts_col_name: comments[base_ts], "event": "Comment"}),
                pd.DataFrame({ts_col_name: likes_sent[base_ts], "event": "Like sent"}),
            ],
            ignore_index=True,
        )

    # -----------------------------
    # Matched universe
    # -----------------------------
    matched = df[df[var.col_match_id].notna()].copy()

    # -----------------------------
    # Like received (ALWAYS match timestamp)
    # -----------------------------
    received = matched[
        is_received.reindex(matched.index, fill_value=False)
        & matched[var.col_match_timestamp].notna()
    ]

    like_received_events = pd.DataFrame(
        {ts_col_name: received[var.col_match_timestamp], "event": "Like received"}
    ).drop_duplicates()

    # -----------------------------
    # Match
    # -----------------------------
    match_ts = var.col_like_timestamp if use_like_timestamp else var.col_match_timestamp
    match_events = matched[matched[match_ts].notna()]

    match_events = pd.DataFrame(
        {ts_col_name: match_events[match_ts], "event": "Match"}
    ).drop_duplicates()

    # -----------------------------
    # Conversation
    # -----------------------------
    msg_cnt = matched[var.col_conversation_message_count].fillna(0)
    span_min = matched[var.col_conversation_span_minutes].fillna(0)
    is_convo = (msg_cnt >= min_messages) & (span_min >= min_minutes)

    convo_ts = var.col_like_timestamp if use_like_timestamp else var.col_first_message_timestamp
    convo = matched[is_convo & matched[convo_ts].notna()]

    convo_events = pd.DataFrame(
        {ts_col_name: convo[convo_ts], "event": "Conversation"}
    ).drop_duplicates()

    # -----------------------------
    # We met / My type
    # -----------------------------
    is_we_met = matched[var.col_we_met].fillna(False).astype(bool)
    we_met_ts = var.col_like_timestamp if use_like_timestamp else var.col_we_met_timestamp

    we_met = matched[is_we_met & matched[we_met_ts].notna()]
    we_met_events = pd.DataFrame(
        {ts_col_name: we_met[we_met_ts], "event": "We met"}
    ).drop_duplicates()

    is_my_type = we_met[var.col_my_type].fillna(False).astype(bool)
    my_type = we_met[is_my_type & we_met[we_met_ts].notna()]

    my_type_events = pd.DataFrame(
        {ts_col_name: my_type[we_met_ts], "event": "My type"}
    ).drop_duplicates()

    # -----------------------------
    # Blocks
    # -----------------------------
    block_ts = var.col_like_timestamp if use_like_timestamp else var.col_block_timestamp
    blocked = matched[
        matched[var.col_block_id].notna() & matched[block_ts].notna()
    ]

    block_events = pd.DataFrame(
        {ts_col_name: blocked[block_ts], "event": "Block"}
    ).drop_duplicates()

    # -----------------------------
    # Combine
    # -----------------------------
    out = pd.concat(
        [
            likes_events,
            like_received_events,
            match_events,
            convo_events,
            we_met_events,
            my_type_events,
            block_events,
        ],
        ignore_index=True,
    )

    out = (
        out.dropna(subset=[ts_col_name])
        .sort_values(ts_col_name)
        .reset_index(drop=True)
    )

    return out

