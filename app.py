from functions.authentification import supabase
import streamlit as st
import functions.authentification as auth
from functions.zip_uploader import uploader
import variables as var

import pandas as pd
import plotly.graph_objects as go

import functions.datasets as ds
import functions.analytics as viz
import numpy as np

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
            
        st.set_page_config(layout="wide")
        
        engagements = ds.like_events_df(user_id)
        st.write(engagements)


        st.header("Engagement Funnel")    
        # Sankey: Engagement Funnel
        sankey_data = ds.sankey_data(engagements)
        fig = viz.sankey(sankey_data, len(engagements))
        st.plotly_chart(fig, width="stretch")


        st.divider()
        st.header("Timing Performance")
        
        # Radial: Time Engagement
        time_table = ds.likes_matches_agg(engagements, "time")
        day_table  = ds.likes_matches_agg(engagements, "day")
        day_time_table  = ds.likes_matches_agg(engagements, "day_time").sort_values(["smoothed_rate", "likes"], ascending=[False, True])


    
        fig_day_radial = viz.radial(day_table)
        fig_time_radial = viz.radial(time_table, day_col="time_bucket")
        
        col1, col2 = st.columns(2)
        col1.plotly_chart(fig_day_radial, width="stretch", config={"scrollZoom": False, "doubleClick": False, "dragmode": False, "displaylogo": False, "modeBarButtonsToRemove": ["zoom","pan","select","lasso","zoomIn","zoomOut","autoScale","resetScale"]})
        col2.plotly_chart(fig_time_radial, width="stretch", config={"scrollZoom": False, "doubleClick": False, "dragmode": False, "displaylogo": False, "modeBarButtonsToRemove": ["zoom","pan","select","lasso","zoomIn","zoomOut","autoScale","resetScale"]})


        best  = (day_time_table .head(3).iloc[:, 0] + " " + day_time_table .head(3).iloc[:, 1]).reset_index(drop=True)
        worst = (day_time_table .tail(3).iloc[:, 0] + " " + day_time_table .tail(3).iloc[:, 1]).reset_index(drop=True)
        
        out = pd.DataFrame({
            "Peak Times": best,
            "Off Times": worst,
        })

        out.index = [""] * len(out)
        
        st.table(out, border="horizontal")



        def rename_columns(df):
            rename_map = {
                "time_bucket": "Time Slot",
                "day_of_week": "Day of Week",
                "likes": "Likes & Comments",
                "matches": "Matches",
                "raw_rate": "Match Rate",
                "smoothed_rate": "Score",
            }
        
            return (
                df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
                  .reset_index(drop=True)
            )
        


        time_table = rename_columns(time_table)
        day_table = rename_columns(day_table)
        day_time_table = rename_columns(day_time_table)


        st.divider()

        st.subheader("Messaging Analytics")
    
        mean_messaging_duration = int(engagements[var.col_conversation_span_minutes].mean())
        fig_box_messaging_duration = viz.horizontal_boxplot(
            engagements[var.col_conversation_span_minutes],
            title="Messaging Duration - Mean: {} Minutes".format(mean_messaging_duration)
        )


        mean_messaging_number = int(engagements[var.col_conversation_message_count].mean())
        fig_box_messaging_number = viz.horizontal_boxplot(
            engagements[var.col_conversation_message_count],
            title="Messages per Session - Mean: {} Minutes".format(mean_messaging_number),
            color = "#EF553B"
        )

        
        st.plotly_chart(fig_box_messaging_duration, width="stretch")
        st.plotly_chart(fig_box_messaging_number, width="stretch")
        
        st.dataframe(time_table, hide_index=True)
        st.dataframe(day_table, hide_index=True)
        st.dataframe(day_time_table, hide_index=True)
    
    # Sign out
    if st.sidebar.button("Sign Out", width="stretch"):
        auth.sign_out()
        st.rerun()


# if not logged in → show login screen
else:
    st.set_page_config(layout="centered")
    auth.auth_screen()
