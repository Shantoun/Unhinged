import pandas as pd
from functions.authentification import supabase
import variables as var
import numpy as np

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

    k_msg_cnt = df["conversation_message_count"].fillna(0).to_numpy() if "conversation_message_count" in df.columns else np.zeros(len(df))
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






def like_events_df(user_id):
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

    # timestamps
    for df in [likes_df, messages_df, matches_df, blocks_df]:
        for c in df.columns:
            if c.endswith("_timestamp"):
                df[c] = pd.to_datetime(df[c], errors="coerce")

    # comments (messages tied to like_id)
    comments = (
        messages_df.dropna(subset=[var.col_like_id])[[var.col_message_id, var.col_like_id]]
        .rename(columns={var.col_message_id: var.col_comment_message_id})
        .drop_duplicates(subset=[var.col_like_id])
    )

    # convo msgs (exclude comments)
    convo_msgs = messages_df[messages_df[var.col_like_id].isna()].copy()

    convo_agg = (
        convo_msgs.groupby(var.col_match_id)
        .agg(
            conversation_message_count=(var.col_message_id, "count"),
            var.col_first_message_timestamp=(var.col_message_timestamp, "min"),
            last_message_ts=(var.col_message_timestamp, "max"),
        )
        .reset_index()
    )
    convo_agg[var.col_conversation_span_minutes] = (
        (convo_agg["last_message_ts"] - convo_agg[var.col_first_message_timestamp]).dt.total_seconds() / 60
    )
    convo_agg = convo_agg.drop(columns=["last_message_ts"])

    # blocks (one per match)
    blocks_agg = (
        blocks_df.dropna(subset=[var.col_match_id])
        .sort_values(var.col_block_timestamp)
        .drop_duplicates(var.col_match_id)
        [[var.col_match_id, var.col_block_id]]
    )

    # matches subset (include match_timestamp)
    matches_sub = matches_df[[var.col_match_id, var.col_match_timestamp, var.col_we_met, var.col_my_type]].copy()

    # sent likes base
    sent = likes_df.copy()
    sent = sent.merge(comments, on=var.col_like_id, how="left")
    sent = sent.merge(matches_sub, on=var.col_match_id, how="left")
    sent = sent.merge(convo_agg, on=var.col_match_id, how="left")
    sent = sent.merge(blocks_agg, on=var.col_match_id, how="left")

    # received likes: matches that don't link to any like.match_id
    like_match_ids = set(likes_df[var.col_match_id].dropna().unique()) if var.col_match_id in likes_df.columns else set()
    received_matches = matches_df[~matches_df[var.col_match_id].isin(like_match_ids)].copy()

    received = received_matches.copy()
    received[var.col_like_id] = pd.NA
    received[var.col_like_timestamp] = pd.NaT
    received[var.col_comment_message_id] = pd.NA

    received = received.merge(convo_agg, on=var.col_match_id, how="left")
    received = received.merge(blocks_agg, on=var.col_match_id, how="left")

    # align columns + concat
    for col in sent.columns:
        if col not in received.columns:
            received[col] = pd.NA
    received = received[sent.columns]

    base_df = pd.concat([sent, received], ignore_index=True)

    base_df["like_direction"] = base_df[var.col_like_id].isna().map({True: "received", False: "sent"})

    base_df = _dedupe_keep_best(base_df)
    return base_df
