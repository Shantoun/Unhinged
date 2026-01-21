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


    ################################################################################## MAIN
    else:
        # Reupload data
        if st.sidebar.button("Upload Data", width="stretch"):
            hinge_sync_dialog()

        # Sign out
        if st.sidebar.button("Sign Out", width="stretch"):
            auth.sign_out()
            st.rerun()



        
        st.set_page_config(layout="wide")
        
        engagements = ds.like_events_df(user_id)
        st.write(engagements)

        st.title("Unhinged")

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Engagement Funnel", "Engagement over Time", "Outbound Timing Performance", "General Distributions", "Engagement Drivers", "Subscription Statistics"])



        with tab1:
            st.header("Engagement Funnel")    
            # Sankey: Engagement Funnel
            sankey_data = ds.sankey_data(engagements)
            fig = viz.sankey(sankey_data, len(engagements))
            st.plotly_chart(fig, width="stretch")
    





        with tab2:

            engagements_over_time = ds.events_over_time_df(engagements)
    
            st.write(engagements_over_time)
    
    
            fig_engagements_over_time, warning = viz.stacked_events_bar_fig(engagements_over_time)
            
            if fig_engagements_over_time is not None:
                st.plotly_chart(fig_engagements_over_time, use_container_width=True)
            if warning:
                st.caption(warning)  

            

    



        with tab3:
            st.header("Messaging Analytics")
        
            mean_messaging_duration = int(engagements[var.col_conversation_span_minutes].mean())
            fig_box_messaging_duration = viz.horizontal_boxplot(
                engagements[var.col_conversation_span_minutes],
                title="Messaging Duration - Mean: {:,} Minutes".format(mean_messaging_duration)
            )
    
            st.plotly_chart(fig_box_messaging_duration, width="stretch")
    
            
            mean_messaging_number = int(engagements[var.col_conversation_message_count].mean())
            fig_box_messaging_number = viz.horizontal_boxplot(
                engagements[var.col_conversation_message_count],
                title="Messages per Session - Mean: {:,} Messages".format(mean_messaging_number),
                color = "#EF553B",
                trace_name="Messages"
            )
            
            st.plotly_chart(fig_box_messaging_number, width="stretch")



            st.header("Time From Like to Match")
    
            mean_like_match_delay = int(engagements[var.col_like_match_delay].mean())
            fig_like_match_delay = viz.horizontal_boxplot(
                engagements[var.col_like_match_delay],
                title="Like to Match Time - Mean: {:,} Minutes".format(mean_like_match_delay),
                color = "#EF553B",
                trace_name="Minutes"
            )
    
            st.plotly_chart(fig_like_match_delay, width="stretch")


        


        with tab4:
            st.header("Messaging Engagement")
    
    
            engagements.rename(columns={
                var.col_avg_message_gap: "Av. Time Between Messages (Mins)",
                var.col_first_message_delay: "Match to First Message Time (Mins)",
                var.col_conversation_message_count: "# of Messages per Session",
            }, inplace=True)
            
    
            columns_scatter = [
                "Av. Time Between Messages (Mins)",
                "Match to First Message Time (Mins)",
                "First Message: Time of Day",
                "First Message: Day of Week",
                "First Message: Daytime",
            ]
            
            colx = st.selectbox("", columns_scatter)
    
            
            fig = viz.scatter_plot(
                engagements,
                x_key=colx,
                y_col="# of Messages per Session",
                first_ts_col=var.col_first_message_timestamp,
                title="Messaging Analytics",
            )
            
            st.plotly_chart(fig, width="stretch")
    
    
    
            # I know how this looks lol, shut up...
            engagements.rename(columns={
                "Av. Time Between Messages (Mins)": var.col_avg_message_gap,
                "Match to First Message Time (Mins)": var.col_first_message_delay,
                "# of Messages per Session": var.col_conversation_message_count,
            }, inplace=True)
            




        
        with tab5:

            st.header("Likes & Comments Timing Performance")
            
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

        
            
            st.dataframe(time_table, hide_index=True)
            st.dataframe(day_table, hide_index=True)
            st.dataframe(day_time_table, hide_index=True)  
    
    
    

    



        

    


# if not logged in → show login screen
else:
    st.set_page_config(layout="centered")
    auth.auth_screen()
