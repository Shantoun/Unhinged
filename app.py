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

        



        _TIME_BINS = [
            (0, 4,  "12 - 4am"),
            (4, 8,  "4 - 8am"),
            (8, 12, "8am - 12pm"),
            (12, 16,"12 - 4pm"),
            (16, 20,"4 - 8pm"),
            (20, 24,"8pm - 12am"),
        ]


        def relationship_summary(df, x_key, y_col, first_ts_col, min_n=25, min_groups=1, min_per_group=1):
            import numpy as np
            import pandas as pd
            from scipy.stats import spearmanr
        
            DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            TIME_BIN_ORDER = [label for _, _, label in _TIME_BINS]
            DAYTIME_ORDER = [f"{d} • {t}" for d in DAY_ORDER for t in TIME_BIN_ORDER]
        
            def _time_bin_label(ts: pd.Series) -> pd.Series:
                h = ts.dt.hour
                out = pd.Series(index=ts.index, dtype="object")
                for start, end, label in _TIME_BINS:
                    out[(h >= start) & (h < end)] = label
                return out
        
            y = pd.to_numeric(df[y_col], errors="coerce")
        
            # categorical X from first message timestamp
            if x_key in {"First Message: Day of Week", "First Message: Time of Day", "First Message: Daytime"}:
                ts = pd.to_datetime(df[first_ts_col], errors="coerce")
        
                if x_key == "First Message: Day of Week":
                    x = ts.dt.day_name()
                    order = DAY_ORDER
                elif x_key == "First Message: Time of Day":
                    x = _time_bin_label(ts)
                    order = TIME_BIN_ORDER
                else:
                    x = ts.dt.day_name().astype(str) + " • " + _time_bin_label(ts).astype(str)
                    order = DAYTIME_ORDER
        
                tmp = pd.DataFrame({"x": x, "y": y}).dropna()
                if tmp.empty:
                    return {"r": None, "label": "Insufficient data to assess a relationship", "n": 0}
        
                tmp["x"] = pd.Categorical(tmp["x"].astype(str), categories=order, ordered=True)
                tmp = tmp[tmp["x"].cat.codes >= 0]
        
                g = (
                    tmp.groupby("x", observed=True)["y"]
                    .agg(mean="mean", n="size")
                    .reset_index()
                )
                g = g[g["n"] >= min_per_group]
                if len(g) < min_groups:
                    return {"r": None, "label": "Insufficient data to assess a relationship", "n": int(len(tmp)), "groups": int(len(g))}
        
                idx = g["x"].cat.codes.astype(float).to_numpy()
                vals = g["mean"].to_numpy(dtype=float)
        
                r, _ = spearmanr(idx, vals)
        
                ar = abs(r)
                if ar < 0.1:
                    label = "No meaningful relationship"
                elif ar < 0.3:
                    label = f"Weak {'positive' if r > 0 else 'negative'} relationship"
                elif ar < 0.5:
                    label = f"Moderate {'positive' if r > 0 else 'negative'} relationship"
                else:
                    label = f"Strong {'positive' if r > 0 else 'negative'} relationship"
        
                return {"r": float(r), "label": label, "n": int(len(tmp)), "groups": int(len(g))}
        
            # numeric X
            x = pd.to_numeric(df[x_key], errors="coerce")
            tmp = pd.DataFrame({"x": x, "y": y}).dropna()
        
            if len(tmp) < min_n:
                return {"r": None, "label": "Insufficient data to assess a relationship", "n": int(len(tmp))}
        
            r, _ = spearmanr(tmp["x"], tmp["y"])
        
            ar = abs(r)
            if ar < 0.1:
                label = "No meaningful relationship"
            elif ar < 0.3:
                label = f"Weak {'positive' if r > 0 else 'negative'} relationship"
            elif ar < 0.5:
                label = f"Moderate {'positive' if r > 0 else 'negative'} relationship"
            else:
                label = f"Strong {'positive' if r > 0 else 'negative'} relationship"
        
            return {"r": float(r), "label": label, "n": int(len(tmp))}
                
                


        result = relationship_summary(
            engagements,
            x_key=colx,
            y_col="# of Messages per Session",
            first_ts_col=var.col_first_message_timestamp,
        )
        
        st.caption(result["label"])
        








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
