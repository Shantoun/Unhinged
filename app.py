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






        st.divider()
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





        st.divider()
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
        




        
        st.divider()
        st.header("Time From Like to Match")

        mean_like_match_delay = int(engagements[var.col_like_match_delay].mean())
        fig_like_match_delay = viz.horizontal_boxplot(
            engagements[var.col_like_match_delay],
            title="Like to Match Time - Mean: {:,} Minutes".format(mean_like_match_delay),
            color = "#EF553B",
            trace_name="Minutes"
        )

        st.plotly_chart(fig_like_match_delay, width="stretch")



        def events_over_time_df(
            data,
            min_messages=2,
            min_minutes=5,
            join_comments_and_likes_sent=False,
            use_like_timestamp=True,
        ):
            import pandas as pd
        
            df = data.copy()
        
            ts_col_name = "Like Timestamp" if use_like_timestamp else "Event Timestamp"
        
            # ensure timestamps are datetime
            for c in [
                var.col_like_timestamp,
                var.col_match_timestamp,
                var.col_first_message_timestamp,
                var.col_we_met_timestamp,
                var.col_block_timestamp,
            ]:
                if c in df.columns:
                    df[c] = pd.to_datetime(df[c], errors="coerce")
        
            is_sent = df[var.col_like_direction].eq("sent")
            is_received = df[var.col_like_direction].eq("received")
            has_comment = df[var.col_comment_message_id].notna()
        
            # -----------------------------
            # Likes / Comments
            # -----------------------------
            base_ts = var.col_like_timestamp if use_like_timestamp else var.col_like_timestamp
        
            if join_comments_and_likes_sent:
                sent_any = df[is_sent & df[base_ts].notna()]
                likes_events = pd.DataFrame(
                    {ts_col_name: sent_any[base_ts], "event": "Comments & Likes Sent"}
                )
            else:
                comments = df[is_sent & has_comment & df[base_ts].notna()]
                likes_sent = df[is_sent & ~has_comment & df[base_ts].notna()]
        
                likes_events = pd.concat(
                    [
                        pd.DataFrame({ts_col_name: comments[base_ts], "event": "Comment"}),
                        pd.DataFrame({ts_col_name: likes_sent[base_ts], "event": "Like sent"}),
                    ],
                    ignore_index=True,
                )
        
            # -----------------------------
            # Matched universe
            # -----------------------------
            matched = df[df[var.col_match_id].notna()].copy()
        
            # -----------------------------
            # Like received (ALWAYS match timestamp)
            # -----------------------------
            received = matched[
                is_received.reindex(matched.index, fill_value=False)
                & matched[var.col_match_timestamp].notna()
            ]
        
            like_received_events = pd.DataFrame(
                {ts_col_name: received[var.col_match_timestamp], "event": "Like received"}
            ).drop_duplicates()
        
            # -----------------------------
            # Match
            # -----------------------------
            match_ts = var.col_like_timestamp if use_like_timestamp else var.col_match_timestamp
            match_events = matched[matched[match_ts].notna()]
        
            match_events = pd.DataFrame(
                {ts_col_name: match_events[match_ts], "event": "Match"}
            ).drop_duplicates()
        
            # -----------------------------
            # Conversation
            # -----------------------------
            msg_cnt = matched[var.col_conversation_message_count].fillna(0)
            span_min = matched[var.col_conversation_span_minutes].fillna(0)
            is_convo = (msg_cnt >= min_messages) & (span_min >= min_minutes)
        
            convo_ts = var.col_like_timestamp if use_like_timestamp else var.col_first_message_timestamp
            convo = matched[is_convo & matched[convo_ts].notna()]
        
            convo_events = pd.DataFrame(
                {ts_col_name: convo[convo_ts], "event": "Conversation"}
            ).drop_duplicates()
        
            # -----------------------------
            # We met / My type
            # -----------------------------
            is_we_met = matched[var.col_we_met].fillna(False).astype(bool)
            we_met_ts = var.col_like_timestamp if use_like_timestamp else var.col_we_met_timestamp
        
            we_met = matched[is_we_met & matched[we_met_ts].notna()]
            we_met_events = pd.DataFrame(
                {ts_col_name: we_met[we_met_ts], "event": "We met"}
            ).drop_duplicates()
        
            is_my_type = we_met[var.col_my_type].fillna(False).astype(bool)
            my_type = we_met[is_my_type & we_met[we_met_ts].notna()]
        
            my_type_events = pd.DataFrame(
                {ts_col_name: my_type[we_met_ts], "event": "My type"}
            ).drop_duplicates()
        
            # -----------------------------
            # Blocks
            # -----------------------------
            block_ts = var.col_like_timestamp if use_like_timestamp else var.col_block_timestamp
            blocked = matched[
                matched[var.col_block_id].notna() & matched[block_ts].notna()
            ]
        
            block_events = pd.DataFrame(
                {ts_col_name: blocked[block_ts], "event": "Block"}
            ).drop_duplicates()
        
            # -----------------------------
            # Combine
            # -----------------------------
            out = pd.concat(
                [
                    likes_events,
                    like_received_events,
                    match_events,
                    convo_events,
                    we_met_events,
                    my_type_events,
                    block_events,
                ],
                ignore_index=True,
            )
        
            out = (
                out.dropna(subset=[ts_col_name])
                .sort_values(ts_col_name)
                .reset_index(drop=True)
            )
        
            return out



        deef = events_over_time_df(engagements)

        st.write(deef)


        def stacked_events_bar_fig(events_df, ts_col=None, title="Events over time"):
            import pandas as pd
            import plotly.express as px
            import streamlit as st
        
            df = events_df.copy()
        
            # infer timestamp col
            if ts_col is None:
                candidates = [c for c in df.columns if "timestamp" in c.lower()]
                ts_col = candidates[0] if candidates else df.columns[0]
        
            df[ts_col] = pd.to_datetime(df[ts_col], errors="coerce")
            if pd.api.types.is_datetime64tz_dtype(df[ts_col]):
                df[ts_col] = df[ts_col].dt.tz_convert(None)
        
            df = df.dropna(subset=[ts_col, "event"])
            if df.empty:
                return None, None
        
            tmin = df[ts_col].min()
            tmax = df[ts_col].max()
            span = tmax - tmin
        
            def ge_offset(dt_min, dt_max, offset):
                return dt_max >= (dt_min + offset)
        
            one_day = pd.Timedelta(days=1)
        
            # -------- group-by selector (dynamic options) --------
            if span < one_day:
                bucket = "All"
            else:
                opts = ["Day"]
                if span >= pd.Timedelta(days=7):
                    opts = ["Week"] + opts
                if ge_offset(tmin, tmax, pd.DateOffset(months=1)):
                    opts = ["Month"] + opts
                if ge_offset(tmin, tmax, pd.DateOffset(months=3)):
                    opts = ["Quarter"] + opts
                if ge_offset(tmin, tmax, pd.DateOffset(years=1)):
                    opts = ["Year"] + opts
        
                bucket = st.selectbox("Group by", opts, index=0)
        
            # -------- bucketing + pretty hover labels --------
            if bucket == "All":
                df["_bucket_dt"] = pd.Timestamp("1970-01-01")
                df["_bucket_label"] = "All time"
                df["_hover_label"] = "All time"
        
            elif bucket == "Year":
                df["_bucket_dt"] = df[ts_col].dt.to_period("Y").dt.start_time
                df["_bucket_label"] = df["_bucket_dt"].dt.strftime("%Y")
                df["_hover_label"] = df["_bucket_label"]
        
            elif bucket == "Quarter":
                p = df[ts_col].dt.to_period("Q")
                df["_bucket_dt"] = p.dt.start_time
                df["_bucket_label"] = p.astype(str)               # 2026Q4
                df["_hover_label"] = df["_bucket_label"].str.replace("Q", " Q", regex=False)  # 2026 Q4
        
            elif bucket == "Month":
                df["_bucket_dt"] = df[ts_col].dt.to_period("M").dt.start_time
                df["_bucket_label"] = df["_bucket_dt"].dt.strftime("%Y-%m")   # stable x ordering
                df["_hover_label"] = df["_bucket_dt"].dt.strftime("%b %Y")    # Jan 2026
        
            elif bucket == "Week":
                df["_bucket_dt"] = df[ts_col].dt.to_period("W-MON").dt.start_time
                week_end = df["_bucket_dt"] + pd.Timedelta(days=6)
                df["_bucket_label"] = df["_bucket_dt"].dt.strftime("%Y-%m-%d")
                df["_hover_label"] = (
                    df["_bucket_dt"].dt.strftime("%d.%m.%Y") + " – " + week_end.dt.strftime("%d.%m.%Y")
                )
        
            else:  # Day
                df["_bucket_dt"] = df[ts_col].dt.floor("D")
                df["_bucket_label"] = df["_bucket_dt"].dt.strftime("%Y-%m-%d")
                df["_hover_label"] = df["_bucket_dt"].dt.strftime("%d.%m.%Y")
        
            # -------- aggregate --------
            agg = (
                df.groupby(["_bucket_label", "_hover_label", "event"], as_index=False)
                  .size()
                  .rename(columns={"size": "count"})
            )
        
            # chronological order
            sort_key = (
                df.drop_duplicates("_bucket_label")[["_bucket_label", "_bucket_dt"]]
                  .sort_values("_bucket_dt")
            )
            agg = agg.merge(sort_key, on="_bucket_label", how="left").sort_values("_bucket_dt")
        
            # stack + legend order (bottom -> top)
            order = [
                "Like sent",
                "Comment",
                "Like received",
                "Match",
                "Conversation",
                "We met",
                "My type",
                "Block",
            ]
            extras = [e for e in agg["event"].unique().tolist() if e not in order]
            category_order = order + sorted(extras)
        
            fig = px.bar(
                agg,
                x="_bucket_label",
                y="count",
                color="event",
                barmode="stack",
                title=title,
                category_orders={"event": category_order},
                custom_data=["_hover_label", "event", "count"],
            )
        
            # clean hover
            fig.update_traces(
                hovertemplate="%{customdata[0]}<br>%{customdata[1]}: %{customdata[2]}<extra></extra>"
            )
        
            # remove legend title, keep legend ordered
            fig.update_layout(
                legend_title_text="",
                xaxis_title=None,
                yaxis_title=None,
            )
        
            # zoom only on X (lock Y)
            fig.update_yaxes(fixedrange=True)
        
            # -------- partial bucket warning --------
            warning = None
            if bucket != "All":
                tmin0 = pd.Timestamp(tmin).tz_localize(None) if getattr(tmin, "tzinfo", None) else pd.Timestamp(tmin)
                tmax0 = pd.Timestamp(tmax).tz_localize(None) if getattr(tmax, "tzinfo", None) else pd.Timestamp(tmax)
        
                def bounds(dt, mode):
                    dt = pd.Timestamp(dt).tz_localize(None) if getattr(dt, "tzinfo", None) else pd.Timestamp(dt)
                    if mode == "Year":
                        start = pd.Timestamp(dt.year, 1, 1)
                        end = pd.Timestamp(dt.year + 1, 1, 1)
                    elif mode == "Quarter":
                        q = ((dt.month - 1) // 3) * 3 + 1
                        start = pd.Timestamp(dt.year, q, 1)
                        end = start + pd.DateOffset(months=3)
                    elif mode == "Month":
                        start = pd.Timestamp(dt.year, dt.month, 1)
                        end = start + pd.DateOffset(months=1)
                    elif mode == "Week":
                        start = dt.normalize() - pd.Timedelta(days=dt.weekday())
                        end = start + pd.Timedelta(days=7)
                    else:  # Day
                        start = dt.normalize()
                        end = start + pd.Timedelta(days=1)
                    return start, end
        
                first_bucket_start, _ = bounds(tmin0, bucket)
                _, last_bucket_end = bounds(tmax0, bucket)
        
                if (tmin0 > first_bucket_start) or (tmax0 < last_bucket_end):
                    warning = "⚠️ Time buckets may be partial at the edges (data doesn’t cover full calendar buckets)."
        
            return fig, warning

        
        fig, warning = stacked_events_bar_fig(deef, ts_col="Event Timestamp")
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
        if warning:
            st.caption(warning)  
        
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
    
    # Sign out
    if st.sidebar.button("Sign Out", width="stretch"):
        auth.sign_out()
        st.rerun()


# if not logged in → show login screen
else:
    st.set_page_config(layout="centered")
    auth.auth_screen()
