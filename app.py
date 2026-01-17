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






        _TIME_BINS = [
            (0, 4,  "12–4am"),
            (4, 8,  "4–8am"),
            (8, 12, "8am–12pm"),
            (12, 16,"12–4pm"),
            (16, 20,"4–8pm"),
            (20, 24,"8pm–12am"),
        ]
        _TIME_ORDER = [label for _, _, label in _TIME_BINS]
        _DOW_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        
        def _time_bucket_from_dt(dt_series):
            hrs = dt_series.dt.hour
            out = pd.Series(pd.NA, index=dt_series.index, dtype="object")
            for start, end, label in _TIME_BINS:
                out[(hrs >= start) & (hrs < end)] = label
            return pd.Categorical(out, categories=_TIME_ORDER, ordered=True)
        
        def _dow_from_dt(dt_series):
            return pd.Categorical(dt_series.dt.day_name(), categories=_DOW_ORDER, ordered=True)
        
        def likes_matches_agg(data, by="time", tz="America/Toronto"):
            """
            by: "time" (4-hour buckets) or "day" (day of week)
            returns a dataframe with columns: [group, likes, matches]
            """
            if by not in {"time", "day"}:
                raise ValueError('by must be "time" or "day"')
        
            df = data.copy()
        
            # Only sent likes
            if "like_direction" in df.columns:
                df = df[df.like_direction == "sent"].copy()
        
            # Parse timestamps (assumes ISO strings with Z/UTC like your sample)
            df.like_timestamp = pd.to_datetime(df.like_timestamp, utc=True, errors="coerce").dt.tz_convert(tz)
            df.match_timestamp = pd.to_datetime(df.match_timestamp, utc=True, errors="coerce").dt.tz_convert(tz)
        
            if by == "time":
                like_group = _time_bucket_from_dt(df.like_timestamp)
                match_group = _time_bucket_from_dt(df.match_timestamp)
                group_name = "time_bucket"
                group_order = _TIME_ORDER
            else:
                like_group = _dow_from_dt(df.like_timestamp)
                match_group = _dow_from_dt(df.match_timestamp)
                group_name = "day_of_week"
                group_order = _DOW_ORDER
        
            likes = (
                df.groupby(like_group, dropna=False)["like_id"]
                  .nunique()
                  .reindex(group_order, fill_value=0)
                  .rename("likes")
            )
        
            matches = (
                df.dropna(subset=["match_id", "match_timestamp"])
                  .groupby(match_group)["match_id"]
                  .nunique()
                  .reindex(group_order, fill_value=0)
                  .rename("matches")
            )
        
            out = pd.concat([likes, matches], axis=1).reset_index()
            out = out.rename(columns={"index": group_name, 0: group_name})
            out[group_name] = out[group_name].astype(str)
            out["likes"] = out["likes"].astype(int)
            out["matches"] = out["matches"].astype(int)
            return out
        
        def likes_matches_aggs(data, tz="America/Toronto"):
            """Returns both tables in a dict: {'time': df_time, 'day': df_day}"""
            return {
                "time": likes_matches_agg(data, by="time", tz=tz),
                "day":  likes_matches_agg(data, by="day",  tz=tz),
            }



        time_table = likes_matches_agg(data, "time")
        day_table  = likes_matches_agg(data, "day")


        st.write(time_table)
        st.write(day_table)


    
    

    
    # Sign out
    if st.sidebar.button("Sign Out", width="stretch"):
        auth.sign_out()
        st.rerun()


# if not logged in → show login screen
else:
    st.set_page_config(layout="centered")
    auth.auth_screen()
