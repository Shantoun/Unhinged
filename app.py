from functions.authentification import supabase
import streamlit as st
import functions.authentification as auth
from functions.zip_uploader import uploader
import variables as var

import pandas as pd
import plotly.graph_objects as go

import functions.datasets as ds



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
            

        df = ds.like_events_df(user_id)
        st.write(df)

        def sankey_data(data, min_messages=2, min_minutes=5):
            import pandas as pd
        
            # --- entry groups (mutually exclusive) ---
            is_sent = data["like_direction"].eq("sent")
            is_received = data["like_direction"].eq("received")
            has_comment = data["comment_message_id"].notna()
        
            comments = data[is_sent & has_comment]
            likes_sent = data[is_sent & ~has_comment]
            likes_received = data[is_received]
        
            # --- conversation classification ---
            msg_cnt = data["conversation_message_count"].fillna(0)
            span_min = data["conversation_span_minutes"].fillna(0)
        
            is_convo = (msg_cnt >= min_messages) & (span_min >= min_minutes)
        
            # outcomes
            is_we_met = data["we_met"].fillna(False).astype(bool)
            is_blocked = data["block_id"].notna()
        
            # split we_met / blocks into "via conversation" vs "direct from matches"
            we_met_via_convo = data[is_convo & is_we_met]
            we_met_direct = data[~is_convo & is_we_met]
        
            blocks_via_convo = data[is_convo & is_blocked]
            blocks_direct = data[~is_convo & is_blocked]
        
            my_type = data[is_we_met & data["my_type"].fillna(False).astype(bool)]
        
            flows = [
                ("Comments", "Matches", comments["match_id"].nunique()),
                ("Likes", "Matches", likes_sent["match_id"].nunique()),
                ("Received", "Matches", likes_received["match_id"].nunique()),
        
                ("Matches", "Conversations", data[is_convo]["match_id"].nunique()),
        
                ("Matches", "We met", we_met_direct["match_id"].nunique()),
                ("Conversations", "We met", we_met_via_convo["match_id"].nunique()),
        
                ("Matches", "Blocks", blocks_direct["match_id"].nunique()),
                ("Conversations", "Blocks", blocks_via_convo["match_id"].nunique()),
        
                ("We met", "My type", my_type["match_id"].nunique()),
            ]
        
            sankey_df = (
                pd.DataFrame(flows, columns=["Source", "Target", "Value"])
                .groupby(["Source", "Target"], as_index=False)["Value"].sum()
                .query("Value > 0")
            )
        
            return sankey_df
            
        
        sankey(df)



    
    # Sign out
    if st.sidebar.button("Sign Out", width="stretch"):
        auth.sign_out()
        st.rerun()


# if not logged in → show login screen
else:
    auth.auth_screen()
