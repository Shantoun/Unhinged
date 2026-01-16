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
            

        
        def build_like_base(likes_df, messages_df, matches_df, blocks_df):
        
            # --- comments (messages tied to like_id) ---
            comments = (
                messages_df
                .dropna(subset=["like_id"])
                [["message_id", "like_id"]]
                .rename(columns={"message_id": "comment_message_id"})
            )
        
            # --- conversation messages (exclude comments) ---
            convo_msgs = messages_df[messages_df["like_id"].isna()].copy()
        
            convo_agg = (
                convo_msgs
                .groupby("match_id")
                .agg(
                    conversation_message_count=("message_id", "count"),
                    first_message_ts=("message_timestamp", "min"),
                    last_message_ts=("message_timestamp", "max"),
                )
                .reset_index()
            )
        
            convo_agg["conversation_span_minutes"] = (
                (convo_agg["last_message_ts"] - convo_agg["first_message_ts"])
                .dt.total_seconds() / 60
            )
        
            convo_agg = convo_agg.drop(columns=["first_message_ts", "last_message_ts"])
        
            # --- blocks (one per match) ---
            blocks_agg = (
                blocks_df
                .dropna(subset=["match_id"])
                .sort_values("block_timestamp")
                .drop_duplicates("match_id")
                [["match_id", "block_id"]]
            )
        
            # --- build base table ---
            base = likes_df.copy()
        
            base = base.merge(
                comments,
                on="like_id",
                how="left"
            )
        
            base = base.merge(
                matches_df[["match_id", "we_met", "my_type"]],
                on="match_id",
                how="left"
            )
        
            base = base.merge(
                convo_agg,
                on="match_id",
                how="left"
            )
        
            base = base.merge(
                blocks_agg,
                on="match_id",
                how="left"
            )
        
            return base
        
        
        # fetch data
        likes_df = (
            supabase.table("likes")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        likes_df = pd.DataFrame(likes_df.data or [])
        
        messages_df = (
            supabase.table("messages")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        messages_df = pd.DataFrame(messages_df.data or [])
        
        matches_df = (
            supabase.table("matches")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        matches_df = pd.DataFrame(matches_df.data or [])
        
        blocks_df = (
            supabase.table("blocks")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        blocks_df = pd.DataFrame(blocks_df.data or [])
        
        # coerce timestamps once
        for df in [messages_df, blocks_df]:
            for c in df.columns:
                if c.endswith("_timestamp"):
                    df[c] = pd.to_datetime(df[c], errors="coerce")
        
        # build base table
        base_df = build_like_base(
            likes_df=likes_df,
            messages_df=messages_df,
            matches_df=matches_df,
            blocks_df=blocks_df,
        )
        
        # inspect
        st.write(base_df)
        st.write("rows:", len(base_df))





    



    
    # Sign out
    if st.sidebar.button("Sign Out", width="stretch"):
        auth.sign_out()
        st.rerun()


# if not logged in → show login screen
else:
    auth.auth_screen()
