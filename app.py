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


        mean_messaging_number = int(engagements[var.col_conversation_message_count].mean())
        fig_box_messaging_number = viz.horizontal_boxplot(
            engagements[var.col_conversation_message_count],
            title="Messages per Session - Mean: {:,} Messages".format(mean_messaging_number),
            color = "#EF553B",
            trace_name="Messages"
        )

        
        st.plotly_chart(fig_box_messaging_duration, width="stretch")
        st.plotly_chart(fig_box_messaging_number, width="stretch")





        st.divider()
        st.header("Messaging Engagement")

 
        
        _TIME_BINS = [
            (0, 4,  "12 - 4am"),
            (4, 8,  "4 - 8am"),
            (8, 12, "8am - 12pm"),
            (12, 16,"12 - 4pm"),
            (16, 20,"4 - 8pm"),
            (20, 24,"8pm - 12am"),
        ]
        
        def scatter_plot(
            df,
            x_key,
            y_col,
            first_ts_col,
            title=None,
            color="#636EFA",
            jitter=0.18,
        ):
            import numpy as np
            import pandas as pd
            import plotly.graph_objects as go
        
            DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            TIME_BIN_ORDER = [label for _, _, label in _TIME_BINS]
            DAYTIME_ORDER = [f"{d} • {t}" for d in DAY_ORDER for t in TIME_BIN_ORDER]
        
            def _time_bin_label(ts: pd.Series) -> pd.Series:
                h = ts.dt.hour
                out = pd.Series(index=ts.index, dtype="object")
                for start, end, label in _TIME_BINS:
                    out[(h >= start) & (h < end)] = label
                return out
        
            ts = pd.to_datetime(df[first_ts_col], errors="coerce")
        
            # Build X
            if x_key == "First Message: Time of Day":
                x_series = _time_bin_label(ts)
                cat_order = TIME_BIN_ORDER
                x_title = x_key
                x_is_cat = True
        
            elif x_key == "First Message: Day of Week":
                x_series = ts.dt.day_name()
                cat_order = DAY_ORDER
                x_title = x_key
                x_is_cat = True
        
            elif x_key == "First Message: Daytime":
                x_series = ts.dt.day_name().astype(str) + " • " + _time_bin_label(ts).astype(str)
                cat_order = DAYTIME_ORDER
                x_title = x_key
                x_is_cat = True
        
            else:
                x_series = pd.to_numeric(df[x_key], errors="coerce")
                x_title = str(x_key)
                x_is_cat = False
        
            y_series = pd.to_numeric(df[y_col], errors="coerce")
        
            if x_is_cat:
                mask = x_series.notna() & y_series.notna()
                x_series = x_series[mask].astype(str)
                y_series = y_series[mask]
        
                x_cat = pd.Categorical(x_series, categories=cat_order, ordered=True)
                codes = x_cat.codes.astype(float)
        
                # drop anything not in categories (-1 code)
                ok = codes >= 0
                codes = codes[ok]
                y_vals = y_series.iloc[np.where(ok)[0]].astype(float).round().astype(int)
        
                rng = np.random.default_rng(42)
                x_plot = codes + rng.uniform(-jitter, jitter, size=len(codes))
        
                fig = go.Figure(
                    go.Scatter(
                        x=x_plot,
                        y=y_vals,
                        mode="markers",
                        marker=dict(color=color),
                        customdata=np.array(x_cat[ok].astype(str)),
                        hovertemplate=(
                            f"{x_title}: %{{customdata}}<br>"
                            f"{y_col}: %{{y:,.0f}}"
                            "<extra></extra>"
                        ),
                    )
                )
        
                fig.update_xaxes(
                    title=x_title,
                    tickmode="array",
                    tickvals=np.arange(len(cat_order)),
                    ticktext=cat_order,
                    zeroline=False,
                )
        
            else:
                mask = x_series.notna() & y_series.notna()
                x_vals = x_series[mask].astype(float).round().astype(int)
                y_vals = y_series[mask].astype(float).round().astype(int)
        
                fig = go.Figure(
                    go.Scatter(
                        x=x_vals,
                        y=y_vals,
                        mode="markers",
                        marker=dict(color=color),
                        hovertemplate=(
                            f"{x_title}: %{{x:,.0f}}<br>"
                            f"{y_col}: %{{y:,.0f}}"
                            "<extra></extra>"
                        ),
                    )
                )
        
                fig.update_xaxes(title=x_title, hoverformat=",.0f")
        
            fig.update_yaxes(title=str(y_col), hoverformat=",.0f")
            fig.update_layout(title=title)
        
            return fig


        columns_scatter = [
            var.col_avg_message_gap,
            var.col_first_message_delay,
            "First Message: Time of Day",
            "First Message: Day of Week",
            "First Message: Daytime",
        ]
        
        colx = st.selectbox("", columns_scatter)
        
        fig = scatter_plot(
            engagements,
            x_key=colx,
            y_col=var.col_conversation_message_count,
            first_ts_col=var.col_first_message_timestamp,
            title="Messaging Analytics",
        )
        
        st.plotly_chart(fig, width="stretch")



        

        
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
