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
        st.plotly_chart(fig, width="stretch")



        # Radial: Time Engagement
        time_table = ds.likes_matches_agg(engagements, "time")
        day_table  = ds.likes_matches_agg(engagements, "day")
        day_time_table  = ds.likes_matches_agg(engagements, "day_time").sort_values(["smoothed_rate", "likes"], ascending=[False, True])

        st.write(time_table)
        st.write(day_table)
        st.write(day_time_table)

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
                hovertemplate="<b>%{theta}</b><br>Score: %{r:.1f}<extra></extra>",
            ))
        
            fig.update_layout(
                polar=dict(
                    angularaxis=dict(
                        rotation=90,
                        direction="clockwise",
                        linecolor="#6B7280",
                        gridcolor="rgba(0,0,0,0.15)",
                    ),
                    radialaxis=dict(
                        tickfont=dict(color="#6B7280"),   # numbers
                        gridcolor="rgba(0,0,0,0.15)",
                        linecolor="#6B7280",
                    ),
                ),
            )
        
            
            return fig

    
        fig_day_radial = radial(day_table)
        fig_time_radial = radial(time_table, day_col="time_bucket")
        
        col1, col2 = st.columns(2)
        col1.plotly_chart(fig_day_radial, width="stretch")
        col2.plotly_chart(fig_time_radial, width="stretch")


        best  = (day_time_table .head(3).iloc[:, 0] + " " + day_time_table .head(3).iloc[:, 1]).reset_index(drop=True)
        worst = (day_time_table .tail(3).iloc[:, 0] + " " + day_time_table .tail(3).iloc[:, 1]).reset_index(drop=True)
        
        out = pd.DataFrame({
            "best_times": best,
            "worst_times": worst,
        })

        
        st.table(out.reset_index(drop=True), border="horizontal")



        #######################################################################################################
        from plotly.subplots import make_subplots
        import streamlit as st
        
        def _add_radial_trace(fig, data, row, col, day_col, rate_col, name):
            df = data[[day_col, rate_col]].copy()
            theta = df[day_col].astype(str).tolist()
            r = df[rate_col].tolist()
        
            theta += [theta[0]]
            r += [r[0]]
        
            fig.add_trace(
                go.Scatterpolar(
                    r=r,
                    theta=theta,
                    mode="lines+markers",
                    line=dict(width=3),
                    marker=dict(size=7),
                    name=name,
                    hovertemplate="<b>%{theta}</b><br>Score: %{r:.1f}<extra></extra>",
                    showlegend=False,
                ),
                row=row, col=col
            )
        
        def radial_pair(
            left_data,
            right_data,
            left_day_col="day_of_week",
            right_day_col="time_bucket",
            rate_col="smoothed_rate",
            left_title="By day",
            right_title="By time",
            title="Score"
        ):
            fig = make_subplots(
                rows=1, cols=2,
                specs=[[{"type": "polar"}, {"type": "polar"}]],
                subplot_titles=(left_title, right_title),
                horizontal_spacing=0.08,
            )
        
            _add_radial_trace(fig, left_data, 1, 1, left_day_col, rate_col, left_title)
            _add_radial_trace(fig, right_data, 1, 2, right_day_col, rate_col, right_title)
        
            # style BOTH polar subplots
            polar_style = dict(
                angularaxis=dict(
                    rotation=90,
                    direction="clockwise",
                    tickfont=dict(color="#6B7280"),
                    linecolor="#6B7280",
                    gridcolor="rgba(0,0,0,0.15)",
                ),
                radialaxis=dict(
                    tickfont=dict(color="#6B7280"),
                    tickcolor="#6B7280",
                    gridcolor="rgba(0,0,0,0.15)",
                    linecolor="#6B7280",
                ),
            )
        
            fig.update_layout(
                title=dict(text=title, x=0.5),
                margin=dict(l=20, r=20, t=60, b=20),
                height=380,
                polar=polar_style,
                polar2=polar_style,
            )
        
            return fig
        
        # usage
        fig = radial_pair(
            day_table, time_table,
            left_day_col="day_of_week",
            right_day_col="time_bucket",
            rate_col="smoothed_rate",
            left_title="Day of week",
            right_title="Time bucket",
            title="Score"
        )
        
        st.plotly_chart(fig, use_container_width=True)











    

    
    
    # Sign out
    if st.sidebar.button("Sign Out", width="stretch"):
        auth.sign_out()
        st.rerun()


# if not logged in → show login screen
else:
    st.set_page_config(layout="centered")
    auth.auth_screen()
