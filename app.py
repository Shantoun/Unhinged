from functions.authentification import supabase
import streamlit as st
import functions.authentification as auth
from functions.zip_uploader import uploader
import variables as var


# initialize the key so it always exists
if var.col_user_id not in st.session_state:
    st.session_state.user_id = None

user_id = st.session_state.user_id



# if logged in → main app
if user_id:

    res = auth.supabase.table(var.table_user_profile) \
        .select("*") \
        .eq(var.col_user_id, user_id) \
        .execute()
    
    has_profile = len(res.data) > 0

    @st.dialog("Sync Your Hinge Data")
    def hinge_sync_dialog():
        done = uploader()
        if done:
            st.rerun()
    
    
    if not has_profile:
        hinge_sync_dialog()
    
    else:
        if st.sidebar.button("Upload Data", width="stretch"):
            hinge_sync_dialog()
            

        
        import streamlit as st
        import pandas as pd
        import plotly.graph_objects as go
        
        # ---------- helpers ----------
        def fetch_df(table, user_id):
            res = (
                supabase
                .table(table)
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            df = pd.DataFrame(res.data or [])

            # normalize timestamps if present
            for col in df.columns:
                if col.endswith("_timestamp"):
                    df[col] = pd.to_datetime(df[col], errors="coerce")
        
            return df
        
        def sankey(data):
            nodes = pd.unique(data[["source", "target"]].values.ravel())
            idx = {n: i for i, n in enumerate(nodes)}
        
            fig = go.Figure(
                go.Sankey(
                    arrangement="snap",
                    node=dict(label=list(nodes), pad=15, thickness=20),
                    link=dict(
                        source=data["source"].map(idx),
                        target=data["target"].map(idx),
                        value=data["value"],
                    ),
                )
            )
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            return fig
        
        def build_sankey_data(
            likes_df,
            matches_df,
            messages_df,
            blocks_df,
            combine_likes=False,
            min_messages=3,
            min_span_minutes=5,
        ):
            # ---- 1) ensure we have required columns even when empty ----
            for df, cols in [
                (likes_df, ["like_id", "match_id", "like_timestamp"]),
                (matches_df, ["match_id", "match_timestamp", "we_met", "my_type"]),
                (messages_df, ["message_id", "match_id", "message_timestamp", "like_id"]),
                (blocks_df, ["match_id", "block_timestamp"]),
            ]:
                for c in cols:
                    if c not in df.columns:
                        df[c] = pd.NA
        
            # ---- 2) like has comment if any message references like_id ----
            comment_like_ids = set(
                messages_df.loc[messages_df["like_id"].notna(), "like_id"].dropna().unique()
            )
        
            likes = likes_df.copy()
            likes["has_comment"] = likes["like_id"].isin(comment_like_ids)
        
            # one like per match (pick earliest like_timestamp)
            likes = (
                likes.dropna(subset=["match_id"])
                .sort_values("like_timestamp")
                .drop_duplicates(subset=["match_id"], keep="first")
                [["match_id", "like_timestamp", "has_comment"]]
            )
        
            # ---- 3) convo stats per match ----
            if len(messages_df):
                convo_stats = (
                    messages_df.dropna(subset=["match_id", "message_timestamp"])
                    .groupby("match_id")
                    .agg(
                        message_count=("message_id", "count"),
                        first_message_ts=("message_timestamp", "min"),
                        last_message_ts=("message_timestamp", "max"),
                    )
                    .reset_index()
                )
                convo_stats["span_minutes"] = (
                    (convo_stats["last_message_ts"] - convo_stats["first_message_ts"])
                    .dt.total_seconds()
                    / 60
                )
            else:
                convo_stats = pd.DataFrame(
                    columns=["match_id", "message_count", "first_message_ts", "last_message_ts", "span_minutes"]
                )
        
            # ---- 4) block timing per match ----
            if len(blocks_df):
                block_stats = (
                    blocks_df.dropna(subset=["match_id", "block_timestamp"])
                    .groupby("match_id")["block_timestamp"]
                    .min()
                    .reset_index(name="block_ts")
                )
            else:
                block_stats = pd.DataFrame(columns=["match_id", "block_ts"])
        
            # ---- 5) build one match-level table (1 row = 1 journey) ----
            m = matches_df.copy()
            m = m.merge(likes, on="match_id", how="left")
            m = m.merge(convo_stats[["match_id", "message_count", "span_minutes", "first_message_ts"]], on="match_id", how="left")
            m = m.merge(block_stats, on="match_id", how="left")
        
            # drop matches that don't have a like attached (optional; keeps the Sankey “likes-started”)
            m = m.dropna(subset=["like_timestamp"])
        
            m["is_convo"] = (
                m["message_count"].fillna(0).astype(int) >= int(min_messages)
            ) & (
                m["span_minutes"].fillna(0) >= float(min_span_minutes)
            )
        
            # initiated by them if match happened before your like OR first message before your like
            m["initiated_by_them"] = (
                (m["match_timestamp"] < m["like_timestamp"])
                | ((m["first_message_ts"].notna()) & (m["first_message_ts"] < m["like_timestamp"]))
            )
        
            m["entry"] = "Likes sent" if combine_likes else m["has_comment"].map(
                {True: "Likes (with comment)", False: "Likes (no comment)"}
            )
        
            m["matched_node"] = m["initiated_by_them"].map(
                {True: "Matched (initiated by them)", False: "Matched (initiated by you)"}
            )
        
            # where does block come from? (avoid double counting)
            m["blocked"] = m["block_ts"].notna()
            m["block_from_convo"] = m["blocked"] & m["is_convo"]
        
            # ---- 6) aggregate edges (counts) ----
            edges = []
        
            # entry -> matched
            edges.append(
                m.groupby(["entry", "matched_node"]).size().reset_index(name="value")
                .rename(columns={"entry": "source", "matched_node": "target"})
            )
        
            # matched -> conversation
            edges.append(
                m[m["is_convo"]]
                .groupby(["matched_node"])
                .size()
                .reset_index(name="value")
                .assign(source=lambda d: d["matched_node"], target="Conversation")
                [["source", "target", "value"]]
            )
        
            # blocks:
            # matched -> blocked (only if blocked and NOT from convo)
            edges.append(
                m[m["blocked"] & (~m["block_from_convo"])]
                .groupby(["matched_node"])
                .size()
                .reset_index(name="value")
                .assign(source=lambda d: d["matched_node"], target="Blocked / Removed")
                [["source", "target", "value"]]
            )
            # conversation -> blocked (blocked after convo)
            edges.append(
                pd.DataFrame(
                    [{"source": "Conversation", "target": "Blocked / Removed", "value": int(m["block_from_convo"].sum())}]
                )
            )
        
            # conversation -> we met (only true)
            edges.append(
                pd.DataFrame(
                    [{"source": "Conversation", "target": "We met", "value": int(((m["is_convo"]) & (m["we_met"] == True)).sum())}]
                )
            )
        
            # we met -> my type / not
            met = m[(m["is_convo"]) & (m["we_met"] == True)]
            edges.append(
                pd.DataFrame([
                    {"source": "We met", "target": "My type", "value": int((met["my_type"] == True).sum())},
                    {"source": "We met", "target": "Not my type", "value": int((met["my_type"] != True).sum())},
                ])
            )
        
            data = pd.concat(edges, ignore_index=True)
            data = data[data["value"] > 0]
        
            return data
        
        @st.cache_data(show_spinner=False)
        def load_and_build(user_id, combine_likes, min_messages, min_span_minutes):
            likes_df = fetch_df("likes", user_id)
            matches_df = fetch_df("matches", user_id)
            messages_df = fetch_df("messages", user_id)
            blocks_df = fetch_df("blocks", user_id)
        
            return build_sankey_data(
                likes_df,
                matches_df,
                messages_df,
                blocks_df,
                combine_likes,
                min_messages,
                min_span_minutes,
            )
        
        # ---------- UI ----------
        combine_likes = st.checkbox("Combine likes")
        min_messages = st.slider("Min messages", 1, 10, 3)
        min_span_minutes = st.slider("Min span (minutes)", 1, 60, 5)
        
        data = load_and_build(user_id, combine_likes, min_messages, min_span_minutes)
        st.plotly_chart(sankey(data), use_container_width=True)








    



    
    # Sign out
    if st.sidebar.button("Sign Out", width="stretch"):
        auth.sign_out()
        st.rerun()


# if not logged in → show login screen
else:
    auth.auth_screen()
