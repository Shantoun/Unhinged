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

        def sankey(
            data,
            min_messages=2,
            min_minutes=5
        ):
            import pandas as pd
        
            flows = []
        
            # ---------- ENTRY STATES ----------
            comments = data[data.comment_id.notna()]
            likes_sent = data[(data.comment_id.isna()) & (data.like_id.notna())]
            likes_received = data[data.is_received_like == True]
        
            flows += [
                ("Comments", "Matches", comments.match_id.nunique()),
                ("Likes", "Matches", likes_sent.match_id.nunique()),
                ("Received", "Matches", likes_received.match_id.nunique()),
            ]
        
            # ---------- CONVERSATIONS ----------
            conversations = data[
                (data.message_count >= min_messages) &
                (data.span_minutes >= min_minutes)
            ]
        
            flows.append(
                ("Matches", "Conversations", conversations.match_id.nunique())
            )
        
            # ---------- WE MET ----------
            we_met = data[data.we_met == True]
        
            flows.append(
                ("Matches", "We met", we_met.match_id.nunique())
            )
        
            # from conversations to we met
            flows.append(
                (
                    "Conversations",
                    "We met",
                    conversations[conversations.we_met == True].match_id.nunique()
                )
            )
        
            # ---------- BLOCKS ----------
            blocks = data[data.block_id.notna()]
        
            flows.append(
                ("Matches", "Blocks", blocks.match_id.nunique())
            )
        
            flows.append(
                (
                    "Conversations",
                    "Blocks",
                    conversations[conversations.block_id.notna()].match_id.nunique()
                )
            )
        
            # ---------- MY TYPE ----------
            my_type = data[(data.we_met == True) & (data.my_type == True)]
        
            flows.append(
                ("We met", "My type", my_type.match_id.nunique())
            )
        
            # ---------- BUILD OUTPUT ----------
            sankey_df = (
                pd.DataFrame(flows, columns=["Source", "Target", "Value"])
                .groupby(["Source", "Target"], as_index=False)
                .sum()
                .query("Value > 0")
                .sort_values("Value", ascending=False)
            )
        
            print(sankey_df)
            return sankey_df
    
        
            sankey(df)



    
    # Sign out
    if st.sidebar.button("Sign Out", width="stretch"):
        auth.sign_out()
        st.rerun()


# if not logged in → show login screen
else:
    auth.auth_screen()
