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
            min_messages=3,
            min_span_minutes=5,
        ):
            edges = []
        
            # --- ensure required cols exist ---
            for df, cols in [
                (likes_df, ["like_id", "match_id", "like_timestamp"]),
                (matches_df, ["match_id", "match_timestamp", "we_met", "my_type"]),
                (messages_df, ["message_id", "match_id", "message_timestamp", "like_id"]),
                (blocks_df, ["match_id", "block_timestamp"]),
            ]:
                for c in cols:
                    if c not in df.columns:
                        df[c] = pd.NA
        
            # --- comment detection: message.like_id != null => like had a comment ---
            comment_like_ids = set(
                messages_df.loc[messages_df["like_id"].notna(), "like_id"].dropna().unique()
            )
        
            likes = likes_df.copy()
            likes["has_comment"] = likes["like_id"].isin(comment_like_ids)
        
            likes_per_match = (
                likes.dropna(subset=["match_id"])
                .sort_values("like_timestamp")
                .drop_duplicates(subset=["match_id"], keep="first")
                [["match_id", "like_timestamp", "has_comment"]]
            )
        
            # --- first message per match (ALWAYS produce column first_message_ts) ---
            msgs = messages_df.dropna(subset=["match_id", "message_timestamp"]).copy()
            if len(msgs) > 0:
                first_msg = (
                    msgs.groupby("match_id")["message_timestamp"]
                    .min()
                    .reset_index()
                    .rename(columns={"message_timestamp": "first_message_ts"})
                )
                convo_stats = (
                    msgs.groupby("match_id")
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
                first_msg = pd.DataFrame({"match_id": [], "first_message_ts": []})
                convo_stats = pd.DataFrame({"match_id": [], "message_count": [], "span_minutes": []})
        
            # --- blocked matches ---
            blocked_ids = set(blocks_df["match_id"].dropna().unique())
        
            # --- match-level table (KEEP ALL MATCHES) ---
            m = matches_df.copy()
            m = m.merge(likes_per_match, on="match_id", how="left")
            m = m.merge(first_msg, on="match_id", how="left")
            m = m.merge(convo_stats[["match_id", "message_count", "span_minutes"]], on="match_id", how="left")
        
            # Entry nodes (level 1)
            m["entry"] = "Likes received"
            m.loc[m["like_timestamp"].notna() & (m["has_comment"] == True), "entry"] = "Comments sent"
            m.loc[m["like_timestamp"].notna() & (m["has_comment"] != True), "entry"] = "Likes sent"
        
            # Initiator: likes received => them; otherwise compare against like_timestamp (safe if first_message_ts missing)
            has_like = m["like_timestamp"].notna()
            m["initiated_by_them"] = True
            m.loc[has_like, "initiated_by_them"] = (
                (m.loc[has_like, "match_timestamp"] < m.loc[has_like, "like_timestamp"])
                | (
                    m.loc[has_like, "first_message_ts"].notna()
                    & (m.loc[has_like, "first_message_ts"] < m.loc[has_like, "like_timestamp"])
                )
            )
        
            m["matched_node"] = m["initiated_by_them"].map(
                {True: "Matched (initiated by them)", False: "Matched (initiated by you)"}
            )
        
            # Conversation flag (ONLY affects Matched -> Conversation)
            m["is_convo"] = (
                m["message_count"].fillna(0).astype(int) >= int(min_messages)
            ) & (
                m["span_minutes"].fillna(0) >= float(min_span_minutes)
            )
        
            m["blocked"] = m["match_id"].isin(blocked_ids)
        
            # --- edges ---
            edges.append(
                m.groupby(["entry", "matched_node"]).size().reset_index(name="value")
                 .rename(columns={"entry": "source", "matched_node": "target"})
            )
        
            edges.append(
                m[m["is_convo"]]
                .groupby("matched_node").size().reset_index(name="value")
                .assign(source=lambda d: d["matched_node"], target="Conversation")
                [["source", "target", "value"]]
            )
        
            edges.append(
                m[m["blocked"]]
                .groupby("matched_node").size().reset_index(name="value")
                .assign(source=lambda d: d["matched_node"], target="Blocked / Removed")
                [["source", "target", "value"]]
            )
        
            edges.append(
                m[m["we_met"] == True]
                .groupby("matched_node").size().reset_index(name="value")
                .assign(source=lambda d: d["matched_node"], target="We met")
                [["source", "target", "value"]]
            )
        
            met = m[m["we_met"] == True]
            edges.append(pd.DataFrame([
                {"source": "We met", "target": "My type", "value": int((met["my_type"] == True).sum())},
                {"source": "We met", "target": "Not my type", "value": int((met["my_type"] != True).sum())},
            ]))
        
            data = pd.concat(edges, ignore_index=True)
            data = data.groupby(["source", "target"], as_index=False)["value"].sum()
            data = data[data["value"] > 0]
            return data
                
        
        @st.cache_data(show_spinner=False)
        def load_and_build(user_id, min_messages, min_span_minutes):
            likes_df = fetch_df("likes", user_id)
            matches_df = fetch_df("matches", user_id)
            messages_df = fetch_df("messages", user_id)
            blocks_df = fetch_df("blocks", user_id)
        
            return build_sankey_data(
                likes_df,
                matches_df,
                messages_df,
                blocks_df,
                min_messages=min_messages,
                min_span_minutes=min_span_minutes,
            )
        
        
        # ---------- UI (assumes user_id exists) ----------
        combine_likes = st.checkbox("Combine likes", value=True)
        min_messages = st.slider("Min messages (conversation)", 1, 10, 3)
        min_span_minutes = st.slider("Min span minutes (conversation)", 1, 60, 5)
        
        data = load_and_build(user_id, min_messages, min_span_minutes)
        st.plotly_chart(sankey(data), use_container_width=True)







    



    
    # Sign out
    if st.sidebar.button("Sign Out", width="stretch"):
        auth.sign_out()
        st.rerun()


# if not logged in → show login screen
else:
    auth.auth_screen()
