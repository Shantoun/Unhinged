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
        
            # --- comment detection: message.like_id != null => that like had a comment ---
            comment_like_ids = set(
                messages_df.loc[messages_df["like_id"].notna(), "like_id"].dropna().unique()
            )
        
            likes = likes_df.copy()
            likes["has_comment"] = likes["like_id"].isin(comment_like_ids)
            likes["entry"] = likes["has_comment"].map({True: "Comments sent", False: "Likes sent"})
        
            # ========== 1) SHOW ALL LIKES (even if unmatched) ==========
            # Use self-loops for unmatched likes so the node width reflects totals without adding a new node.
            unmatched = likes[likes["match_id"].isna()]
            if len(unmatched):
                unmatched_counts = unmatched.groupby("entry").size().reset_index(name="value")
                edges.append(
                    unmatched_counts.assign(source=lambda d: d["entry"], target=lambda d: d["entry"])[
                        ["source", "target", "value"]
                    ]
                )
        
            # ========== 2) BUILD MATCH-LEVEL ENTRY (for matched flows) ==========
            # One like per match (earliest) to classify the match as coming from Likes sent vs Comments sent
            likes_per_match = (
                likes.dropna(subset=["match_id"])
                .sort_values("like_timestamp")
                .drop_duplicates(subset=["match_id"], keep="first")
                [["match_id", "entry"]]
            )
        
            m = matches_df.copy()
            m = m.merge(likes_per_match, on="match_id", how="left")
        
            # Matches with no like record are "Likes received"
            m["entry"] = m["entry"].fillna("Likes received")
        
            # Entry -> Match (single Match node)
            edges.append(
                m.groupby("entry").size().reset_index(name="value")
                .assign(source=lambda d: d["entry"], target="Match")[["source", "target", "value"]]
            )
        
            # ========== 3) CONVERSATION (ONLY A SIDE BRANCH; DOES NOT AFFECT WE_MET / BLOCKS) ==========
            msgs = messages_df.dropna(subset=["match_id", "message_timestamp"]).copy()
            if len(msgs):
                convo_stats = (
                    msgs.groupby("match_id")
                    .agg(
                        message_count=("message_id", "count"),
                        first_ts=("message_timestamp", "min"),
                        last_ts=("message_timestamp", "max"),
                    )
                    .reset_index()
                )
                convo_stats["span_minutes"] = (
                    (convo_stats["last_ts"] - convo_stats["first_ts"]).dt.total_seconds() / 60
                )
        
                convo_ids = set(
                    convo_stats[
                        (convo_stats["message_count"] >= int(min_messages))
                        & (convo_stats["span_minutes"] >= float(min_span_minutes))
                    ]["match_id"]
                )
            else:
                convo_ids = set()
        
            if convo_ids:
                edges.append(pd.DataFrame([{
                    "source": "Match",
                    "target": "Conversation",
                    "value": int(m["match_id"].isin(convo_ids).sum())
                }]))
        
            # ========== 4) BLOCKED / REMOVED (independent of convo sliders) ==========
            blocked_ids = set(blocks_df["match_id"].dropna().unique())
            if blocked_ids:
                edges.append(pd.DataFrame([{
                    "source": "Match",
                    "target": "Blocked / Removed",
                    "value": int(m["match_id"].isin(blocked_ids).sum())
                }]))
        
            # ========== 5) WE MET + TYPE (independent of convo sliders) ==========
            met = m[m["we_met"] == True]
            if len(met):
                edges.append(pd.DataFrame([{
                    "source": "Match",
                    "target": "We met",
                    "value": int(len(met))
                }]))
        
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
