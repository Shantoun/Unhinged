from functions.authentification import supabase
import streamlit as st
import functions.authentification as auth
from functions.zip_uploader import uploader
import variables as var

import pandas as pd
import plotly.graph_objects as go

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
        
            # coerce timestamp columns
            for c in df.columns:
                if c.endswith("_timestamp"):
                    df[c] = pd.to_datetime(df[c], errors="coerce")
        
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
            edges = []
        
            # ---- comment detection: message.like_id != null means the like had a comment ----
            comment_like_ids = set(
                messages_df.loc[messages_df.get("like_id").notna(), "like_id"].dropna().unique()
            ) if ("like_id" in messages_df.columns) else set()
        
            likes = likes_df.copy()
            if "like_id" not in likes.columns:
                likes["like_id"] = pd.NA
            if "match_id" not in likes.columns:
                likes["match_id"] = pd.NA
            if "like_timestamp" not in likes.columns:
                likes["like_timestamp"] = pd.NaT
        
            likes["has_comment"] = likes["like_id"].isin(comment_like_ids)
        
            if combine_likes:
                likes["entry"] = "Likes sent"
            else:
                likes["entry"] = likes["has_comment"].map({True: "Likes (with comment)", False: "Likes (no comment)"})
        
            # ---- Start -> Entry (so entry node width == total likes, even if no match) ----
            start_edges = (
                likes.groupby("entry").size().reset_index(name="value")
                .assign(source="All likes", target=lambda d: d["entry"])
                [["source", "target", "value"]]
            )
            edges.append(start_edges)
        
            # ---- Only matched likes flow forward (Entry -> Matched...) ----
            likes_matched = likes.dropna(subset=["match_id"]).copy()
            if len(likes_matched) == 0 or len(matches_df) == 0:
                return pd.concat(edges, ignore_index=True).query("value > 0")
        
            # one like per match (earliest like_timestamp)
            likes_per_match = (
                likes_matched.sort_values("like_timestamp")
                .drop_duplicates(subset=["match_id"], keep="first")
                [["match_id", "like_timestamp", "entry"]]
            )
        
            # first message per match (for initiator heuristic)
            if len(messages_df) and ("match_id" in messages_df.columns) and ("message_timestamp" in messages_df.columns):
                first_msg = (
                    messages_df.dropna(subset=["match_id", "message_timestamp"])
                    .groupby("match_id")["message_timestamp"]
                    .min()
                    .reset_index(name="first_message_ts")
                )
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
                    (convo_stats["last_message_ts"] - convo_stats["first_message_ts"]).dt.total_seconds() / 60
                )
            else:
                first_msg = pd.DataFrame(columns=["match_id", "first_message_ts"])
                convo_stats = pd.DataFrame(columns=["match_id", "message_count", "span_minutes"])
        
            # blocked matches
            if len(blocks_df) and ("match_id" in blocks_df.columns):
                blocked_ids = set(blocks_df["match_id"].dropna().unique())
            else:
                blocked_ids = set()
        
            # ---- Match-level table (1 row per match) ----
            m = matches_df.copy()
            m = m.merge(likes_per_match, on="match_id", how="inner")  # inner => matches that have a like record
            m = m.merge(first_msg, on="match_id", how="left")
            m = m.merge(convo_stats[["match_id", "message_count", "span_minutes"]], on="match_id", how="left")
        
            # initiator: match before like OR first message before like => them
            m["initiated_by_them"] = (
                (m["match_timestamp"] < m["like_timestamp"])
                | ((m["first_message_ts"].notna()) & (m["first_message_ts"] < m["like_timestamp"]))
            )
        
            m["matched_node"] = m["initiated_by_them"].map(
                {True: "Matched (initiated by them)", False: "Matched (initiated by you)"}
            )
        
            # conversation flag (ONLY affects the Conversation node, NOT we_met/my_type)
            m["is_convo"] = (
                m["message_count"].fillna(0).astype(int) >= int(min_messages)
            ) & (
                m["span_minutes"].fillna(0) >= float(min_span_minutes)
            )
        
            m["blocked"] = m["match_id"].isin(blocked_ids)
        
            # ---- Entry -> Matched ----
            edges.append(
                m.groupby(["entry", "matched_node"]).size().reset_index(name="value")
                 .rename(columns={"entry": "source", "matched_node": "target"})
            )
        
            # ---- Matched -> Conversation (threshold-based; downstream should NOT change) ----
            edges.append(
                m[m["is_convo"]]
                .groupby("matched_node").size().reset_index(name="value")
                .assign(source=lambda d: d["matched_node"], target="Conversation")
                [["source", "target", "value"]]
            )
        
            # ---- Matched -> Blocked/Removed (independent of conversation thresholds) ----
            edges.append(
                m[m["blocked"]]
                .groupby("matched_node").size().reset_index(name="value")
                .assign(source=lambda d: d["matched_node"], target="Blocked / Removed")
                [["source", "target", "value"]]
            )
        
            # ---- Matched -> We met (independent of conversation thresholds) ----
            edges.append(
                m[m.get("we_met") == True]
                .groupby("matched_node").size().reset_index(name="value")
                .assign(source=lambda d: d["matched_node"], target="We met")
                [["source", "target", "value"]]
            )
        
            # ---- We met -> My type / Not my type (independent of conversation thresholds) ----
            met = m[m.get("we_met") == True]
            edges.append(pd.DataFrame([
                {"source": "We met", "target": "My type", "value": int((met.get("my_type") == True).sum())},
                {"source": "We met", "target": "Not my type", "value": int((met.get("my_type") != True).sum())},
            ]))
        
            data = pd.concat(edges, ignore_index=True)
            data = data.groupby(["source", "target"], as_index=False)["value"].sum()
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
                combine_likes=combine_likes,
                min_messages=min_messages,
                min_span_minutes=min_span_minutes,
            )
        
        
        # ---------- UI (assumes user_id exists) ----------
        combine_likes = st.checkbox("Combine likes", value=True)
        min_messages = st.slider("Min messages (conversation)", 1, 10, 3)
        min_span_minutes = st.slider("Min span minutes (conversation)", 1, 60, 5)
        
        data = load_and_build(user_id, combine_likes, min_messages, min_span_minutes)
        st.plotly_chart(sankey(data), use_container_width=True)







    



    
    # Sign out
    if st.sidebar.button("Sign Out", width="stretch"):
        auth.sign_out()
        st.rerun()


# if not logged in → show login screen
else:
    auth.auth_screen()
