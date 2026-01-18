from functions.authentification import supabase
import streamlit as st
import functions.authentification as auth
from functions.zip_uploader import uploader
import variables as var

import pandas as pd
import plotly.graph_objects as go

import functions.datasets as ds
import functions.analytics as viz


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


            
        # Sankey: Engagement Funnel
        sankey_data = ds.sankey_data(engagements)
        fig = viz.sankey(sankey_data, len(engagements))
        st.plotly_chart(fig, use_container_width=True)



        # Radial: Time Engagement
        time_table = ds.likes_matches_agg(engagements, "time")
        day_table  = ds.likes_matches_agg(engagements, "day")
        day_time_table  = ds.likes_matches_agg(engagements, "day_time")

        st.write(time_table)
        st.write(day_table)
        st.write(day_time_table.sort_values(["smoothed_rate", "likes"], ascending=[False, True]))

        def radial(data, day_col="day_of_week", rate_col="smoothed_rate", title="Score by day"):
            df = data[[day_col, rate_col]].copy()
        
            # preserve given order
            theta = df[day_col].astype(str).tolist()
            r = df[rate_col].tolist()
        
            # close the loop
            theta += [theta[0]]
            r += [r[0]]
        
            fig = go.Figure()
        
            fig.add_trace(go.Scatterpolar(
                r=r,
                theta=theta,
                mode="lines+markers",
                line=dict(width=3),
                marker=dict(size=7),
                hovertemplate="<b>%{theta}</b><br>Score: %{r:.3f}<extra></extra>",
            ))
        
            fig.update_layout(
                title=dict(text=title, x=0.5),
                showlegend=False,
                height=360,
                margin=dict(l=20, r=20, t=50, b=20),
                polar=dict(
                    angularaxis=dict(
                        rotation=90,
                        direction="clockwise",
                    ),
                    radialaxis=dict(
                        showgrid=True,
                        gridcolor="rgba(0,0,0,0.12)",
                    ),
                ),
            )
        
            st.plotly_chart(fig, use_container_width=True)
            return fig

    
        radial(day_table)
        radial(time_table, day_col="time_bucket")
        
        
    

    
    # Sign out
    if st.sidebar.button("Sign Out", width="stretch"):
        auth.sign_out()
        st.rerun()


# if not logged in → show login screen
else:
    st.set_page_config(layout="centered")
    auth.auth_screen()
