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
            

        
        def build_base_df(user_id):
            likes_df = pd.DataFrame(
                supabase.table("likes").select("*").eq("user_id", user_id).execute().data or []
            )
            messages_df = pd.DataFrame(
                supabase.table("messages").select("*").eq("user_id", user_id).execute().data or []
            )
            matches_df = pd.DataFrame(
                supabase.table("matches").select("*").eq("user_id", user_id).execute().data or []
            )
            blocks_df = pd.DataFrame(
                supabase.table("blocks").select("*").eq("user_id", user_id).execute().data or []
            )
        
            # timestamps
            for df in [likes_df, messages_df, matches_df, blocks_df]:
                for c in df.columns:
                    if c.endswith("_timestamp"):
                        df[c] = pd.to_datetime(df[c], errors="coerce")
        
            # comments (messages tied to like_id)
            comments = (
                messages_df.dropna(subset=["like_id"])[["message_id", "like_id"]]
                .rename(columns={"message_id": "comment_message_id"})
                .drop_duplicates(subset=["like_id"])
            )
        
            # convo msgs (exclude comments)
            convo_msgs = messages_df[messages_df["like_id"].isna()].copy()
        
            convo_agg = (
                convo_msgs.groupby("match_id")
                .agg(
                    conversation_message_count=("message_id", "count"),
                    first_message_timestamp=("message_timestamp", "min"),
                    last_message_ts=("message_timestamp", "max"),
                )
                .reset_index()
            )
            convo_agg["conversation_span_minutes"] = (
                (convo_agg["last_message_ts"] - convo_agg["first_message_timestamp"]).dt.total_seconds() / 60
            )
            convo_agg = convo_agg.drop(columns=["last_message_ts"])
        
            # blocks (one per match)
            blocks_agg = (
                blocks_df.dropna(subset=["match_id"])
                .sort_values("block_timestamp")
                .drop_duplicates("match_id")
                [["match_id", "block_id"]]
            )
        
            # matches subset (include match_timestamp)
            matches_sub = matches_df[["match_id", "match_timestamp", "we_met", "my_type"]].copy()
        
            # sent likes base
            sent = likes_df.copy()
            sent = sent.merge(comments, on="like_id", how="left")
            sent = sent.merge(matches_sub, on="match_id", how="left")
            sent = sent.merge(convo_agg, on="match_id", how="left")
            sent = sent.merge(blocks_agg, on="match_id", how="left")
        
            # received likes: matches that don't link to any like.match_id
            like_match_ids = set(likes_df["match_id"].dropna().unique()) if "match_id" in likes_df.columns else set()
            received_matches = matches_df[~matches_df["match_id"].isin(like_match_ids)].copy()
        
            received = received_matches.copy()
            received["like_id"] = pd.NA
            received["like_timestamp"] = pd.NaT
            received["comment_message_id"] = pd.NA
        
            received = received.merge(convo_agg, on="match_id", how="left")
            received = received.merge(blocks_agg, on="match_id", how="left")
        
            # align columns + concat
            for col in sent.columns:
                if col not in received.columns:
                    received[col] = pd.NA
            received = received[sent.columns]
        
            base_df = pd.concat([sent, received], ignore_index=True)
        
            base_df["like_direction"] = base_df["like_id"].isna().map({True: "received", False: "sent"})
        
            return base_df

        



        df = build_base_df(user_id)
        st.write(df)
        st.write("rows:", len(df))
        
            



    
    # Sign out
    if st.sidebar.button("Sign Out", width="stretch"):
        auth.sign_out()
        st.rerun()


# if not logged in → show login screen
else:
    auth.auth_screen()
