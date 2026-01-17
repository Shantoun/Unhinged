import pandas as pd
from functions.authentification import supabase
import variables as var


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

    # comments (messages tied to like_id) -> one per like_id
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
            first_message_timestamp=(var.col_message_timestamp, "min"),
            last_message_ts=(var.col_message_timestamp, "max"),
        )
        .reset_index()
    )

    convo_agg[var.col_conversation_span_minutes] = (
        (convo_agg["last_message_ts"] - convo_agg["first_message_timestamp"])
        .dt.total_seconds()
        / 60
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
    matches_sub = matches_df[
        [var.col_match_id, var.col_match_timestamp, var.col_we_met, var.col_my_type]
    ].copy()

    # sent likes base
    sent = likes_df.copy()
    sent = sent.merge(comments, on=var.col_like_id, how="left")
    sent = sent.merge(matches_sub, on=var.col_match_id, how="left")
    sent = sent.merge(convo_agg, on=var.col_match_id, how="left")
    sent = sent.merge(blocks_agg, on=var.col_match_id, how="left")

    # received likes: matches that don't link to any like.match_id
    like_match_ids = (
        set(likes_df[var.col_match_id].dropna().unique())
        if var.col_match_id in likes_df.columns
        else set()
    )
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

    base_df["like_direction"] = base_df[var.col_like_id].isna().map(
        {True: "received", False: "sent"}
    )

    # --------- dedupe: no duplicate like_id (sent) and no duplicate match_id (overall) ---------
    base_df["_we_met"] = base_df[var.col_we_met].fillna(False).astype(bool) if var.col_we_met in base_df.columns else False
    base_df["_my_type"] = base_df[var.col_my_type].fillna(False).astype(bool) if var.col_my_type in base_df.columns else False
    base_df["_has_block"] = base_df[var.col_block_id].notna() if var.col_block_id in base_df.columns else False
    base_df["_has_comment"] = base_df[var.col_comment_message_id].notna() if var.col_comment_message_id in base_df.columns else False
    base_df["_msg_cnt"] = base_df.get("conversation_message_count", pd.Series([0]*len(base_df))).fillna(0)
    base_df["_span"] = base_df.get(var.col_conversation_span_minutes, pd.Series([0]*len(base_df))).fillna(0)

    sort_cols = ["_we_met", "_my_type", "_has_block", "_has_comment", "_msg_cnt", "_span"]
    for c in [var.col_match_timestamp, var.col_like_timestamp, "first_message_timestamp"]:
        if c in base_df.columns:
            sort_cols.append(c)

    asc = [False] * len(sort_cols)

    base_df = base_df.sort_values(by=sort_cols, ascending=asc, na_position="last")

    # unique sent likes by like_id
    sent_part = base_df[base_df[var.col_like_id].notna()].drop_duplicates(
        subset=[var.col_like_id], keep="first"
    )
    # unique received by match_id (like_id is null)
    recv_part = base_df[base_df[var.col_like_id].isna()].drop_duplicates(
        subset=[var.col_match_id], keep="first"
    )

    base_df = pd.concat([sent_part, recv_part], ignore_index=True)

    # enforce match_id uniqueness across all rows
    if var.col_match_id in base_df.columns:
        base_df = base_df.drop_duplicates(subset=[var.col_match_id], keep="first")

    base_df = base_df.drop(columns=[c for c in base_df.columns if c.startswith("_")], errors="ignore")

    return base_df
