from functions.authentification import supabase
import streamlit as st
import functions.authentification as auth
from functions.zip_uploader import uploader
from functions.supabase_ingest import delete_my_data
import variables as var

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

import functions.datasets as ds
import functions.analytics as viz
import numpy as np
from zoneinfo import available_timezones
from streamlit_javascript import st_javascript
from streamlit_theme import st_theme

import smtplib
from email.message import EmailMessage


help_guide_direct = "<em style='color:#6B8E7A;'>Guides for charts and tables are in the sidebar under <b>Quick guides</b>.</em>"
help_guide_direct_w_box = "<em style='color:#6B8E7A;'>Guides for charts, tables and boxplots are in the sidebar under <b>Quick guides</b>.</em>"




st.set_page_config(initial_sidebar_state="collapsed")


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
    

    
        with st.expander("Delete account"):
            st.warning("This will permanently delete your account and all uploaded data. This cannot be undone.")
    
            confirm_text = st.text_input(
                'Type "delete" to confirm',
                key="delete_confirm_text",
            )
    
            if confirm_text.strip().lower() == "delete":
                if st.button("Delete my account", type="primary", width="stretch"):
                    with st.spinner("Deleting your data..."):
                        # 1) delete app data
                        delete_my_data(user_id)
    
                        # 2) delete Supabase Auth user (service role required)
                        auth.supabase_admin.auth.admin.delete_user(user_id)
    
                    # reset session + return to login
                    try:
                        auth.sign_out()
                    except Exception:
                        pass
    
                    st.session_state.user_id = None
                    st.success("Done. Your account has been deleted.")
                    st.rerun()


    
    
    if not has_profile:
        hinge_sync_dialog()


    ################################################################################## MAIN
    else:
        st.set_page_config(layout="wide")
        
        tzs = sorted(available_timezones())
        
        browser_tz = st_javascript("Intl.DateTimeFormat().resolvedOptions().timeZone")
        default_idx = tzs.index(browser_tz) if browser_tz in tzs else 0
        
        with st.sidebar:
            tz = st.selectbox(
                "Timezone",
                tzs,
                index=default_idx,
                help="Auto-detected from your browser. Timestamps do not include timezone data, so choose the timezone you mostly send from for best accuracy."
            )
            st.divider()
        
        # Reupload data
        if st.sidebar.button("Upload More Data", width="stretch"):
            hinge_sync_dialog()

        # Sign out
        if st.sidebar.button("Sign Out", width="stretch"):
            auth.sign_out()
            st.rerun()


        
        # ---- init once (top of app) ----
        if "show_delete_dialog" not in st.session_state:
            st.session_state.show_delete_dialog = False
        
        
        @st.dialog("Delete My Data")
        def delete_data_dialog():
            st.error("This will permanently delete all your data. This cannot be undone.")
        
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Cancel", width="stretch", key="delete_cancel"):
                    st.session_state.show_delete_dialog = False
                    st.rerun()
        
            with c2:
                if st.button("Yes, delete data", type="primary", width="stretch", key="delete_confirm_data"):
                    with st.spinner("Deleting your data..."):
                        delete_my_data(st.session_state.user_id)
        
                    st.session_state.show_delete_dialog = False
                    st.success("Your data has been deleted.")
                    st.rerun()
        
            # ---- extra: delete account (data + auth) ----
            with st.expander("Delete data & account"):
                st.warning("This will permanently delete your account and all associated data.")
        
                confirm_text = st.text_input(
                    'Type "delete" to confirm',
                    key="delete_account_confirm_text",
                )
        
                if confirm_text.strip().lower() == "delete":
                    if st.button(
                        "Delete my data & account",
                        type="primary",
                        width="stretch",
                        key="delete_account_confirm_btn",
                    ):
                        with st.spinner("Deleting your data and account..."):
                            delete_my_data(st.session_state.user_id)
                            auth.supabase_admin.auth.admin.delete_user(st.session_state.user_id)
        
                        try:
                            auth.sign_out()
                        except Exception:
                            pass
        
                        st.session_state.user_id = None
                        st.session_state.show_delete_dialog = False
                        st.success("Your account and data have been deleted.")
                        st.rerun()
                
                
        # ---- sidebar trigger (NO st.rerun here) ----
        if st.sidebar.button("Delete My Data", width="stretch", key="open_delete"):
            st.session_state.show_delete_dialog = True
        
        
        # ---- render dialog in main script flow ----
        if st.session_state.show_delete_dialog:
            delete_data_dialog()





        
        
        def navigation_help_dialog():
            @st.dialog("Quick Guides", width="large")
            def _dialog():
                tab_table, tab_plotly, tab_box = st.tabs(["Tables", "Plotly charts", "Boxplots"])
        
                # -------------------- TAB 1: TABLES --------------------
                with tab_table:
                    st.markdown(
                        """
                            ### Tables
                            
                            Streamlit tables are interactive.
                            
                            **Top-right toolbar (shows when you hover the table):**
                            - **Full screen / expand** (makes the table easier to read, not shown in this example)
                            - **Search** (magnifying glass icon)
                            - **Download** (download the table)
                            
                            **Sorting**
                            - Click a **column name** to sort.
                            - Click again to reverse the sort.
                            
                            **Searching**
                            - Click into the table first, then use **Ctrl/Cmd+F** to find text.
                            - You can also use the **magnifying glass** icon in the table’s top-right toolbar.
                        """
                    )
        
                    # Example table (index hidden, nicer labels)
                    df_demo = pd.DataFrame(
                        {
                            "Name": ["Ava", "Noah", "Mia", "Liam"],
                            "Score": [72, 95, 88, 60],
                            "Group": ["North", "North", "South", "South"],
                        }
                    )
                    st.dataframe(df_demo, use_container_width=True, hide_index=True)
        
                # -------------------- TAB 2: PLOTLY --------------------
                with tab_plotly:
                    st.markdown(
                        """
                            ### Plotly chart controls
                            
                            Plotly charts are interactive.
                            
                            **Modebar (chart tools)**
                            When you **hover over the chart**, a row of tool icons appears in the **top-right** (zoom, pan, reset, download, etc.).  
                            [1min read: Plotly modebar guide](https://plotly.com/chart-studio-help/getting-to-know-the-plotly-modebar/)
                            
                            **Legend (the colored labels)**
                            - **Click** a legend item to hide/show it.
                            - **Double-click** a legend item to show *only that one* (double-click again to reset).
                            
                            **Zoom & reset**
                            - **Drag on the chart** to zoom into an area.
                            - **Double-click** the chart to reset.
                        """
                    )
        
                    df_bar = pd.DataFrame(
                        {
                            "Week": ["W1", "W1", "W1", "W2", "W2", "W2", "W3", "W3", "W3"],
                            "Type": ["Like", "Match", "Message"] * 3,
                            "Count": [30, 12, 5, 25, 14, 7, 18, 10, 9],
                        }
                    )
                    fig_bar = px.bar(df_bar, x="Week", y="Count", color="Type", barmode="stack")
                    st.plotly_chart(fig_bar, use_container_width=True)
        
                # -------------------- TAB 3: BOXPLOTS --------------------
                with tab_box:
                    st.markdown(
                        """
                            ### Boxplots
                            
                            A boxplot summarizes a bunch of numbers without showing every row.
                            
                            **You’ll see these terms on hover:**
                            - **Q1 (25th percentile):** 25% of values are below this.
                            - **Median (50th percentile):** the middle value.
                            - **Q3 (75th percentile):** 75% of values are below this.
                            
                            **What the shapes mean:**
                            - The **shaded box** goes from **Q1 → Q3** (where the “middle half” of the data lives).
                            - The **line inside the box** is the **median**.
                            - The **whiskers** show the “normal range” *excluding outliers*:  
                              think of them as the **lowest** and **highest** values that are still considered part of the main cluster.
                            - **Outliers** are shown as separate dots because they’re **far away** from the main cluster (one very low or very high value can otherwise hide what most of the data looks like).
                            
                            The example below has **one low outlier** and **one high outlier** so you can see both.
                        """
                    )
        
                    np.random.seed(42)
                    core = np.random.normal(loc=50, scale=7, size=220)
                    values = np.concatenate([core, [10, 95]])  # low + high outliers
                    df_box = pd.DataFrame({"Value": values})
        
                    fig_box = px.box(df_box, x="Value", points="outliers", orientation="h")
                    st.plotly_chart(fig_box, use_container_width=True)
        
            _dialog()
        
        
        with st.sidebar:
            if st.button("Quick guides", width="stretch"):
                navigation_help_dialog()
        



        # ---------- email helper ----------
        def send_email(subject, to, body, images=None):
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = st.secrets["SMTP_FROM"]
            msg["To"] = to
            msg.set_content(body)
        
            for img in images or []:
                maintype, subtype = img.type.split("/")
                msg.add_attachment(
                    img.getvalue(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=img.name,
                )
        
            with smtplib.SMTP("smtp.gmail.com", 587) as s:
                s.starttls()
                s.login(st.secrets["SMTP_USER"], st.secrets["SMTP_PASS"])
                s.send_message(msg)
        
        # ---------- dialog ----------
        @st.dialog("Send feedback")
        def feedback_dialog():
            st.link_button("View the GitHub repo", st.secrets.get("GITHUB_REPO_URL", "#"))
        
            feedback = st.text_area(
                label="What should be improved?",
                placeholder="Bug, idea, UI tweak, feature request…",
                height=140,
            )
        
            images = st.file_uploader(
                "Optional screenshots (images only)",
                type=["png", "jpg", "jpeg"],
                accept_multiple_files=True,
            )
        
            user_email = st.session_state.get("user_email", "ahaddadproject@gmail.com")
        
        

            if st.button("Send", type="primary", width="stretch"):
                if not feedback.strip():
                    st.error("Write something first.")
                    return
    
                # email YOU
                send_email(
                    subject="Unhinged feedback",
                    to=st.secrets["SMTP_TO"],
                    body=f"From: {user_email}\n\n{feedback}",
                    images=images,
                )
    
                # confirmation email to USER
                send_email(
                    subject="Your feedback was logged",
                    to=user_email,
                    body=f"Thanks — we received this:\n\n{feedback}",
                    images=images,
                )
    
                st.success("Sent. Thanks 🙏")
                st.rerun()


        
        with st.sidebar:
            st.divider()
            if st.button("Send feedback", use_container_width=True):
                feedback_dialog()


        






        

        
        
        
        engagements = ds.like_events_df(user_id, tz)


        st.title("Unhinged")
        
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([var.tab_engagement_funnel, var.tab_engagement_over_time, var.tab_outbound_timing, var.tab_drivers, var.tab_subscriptions, var.tab_distribution])



        # defaults
        if "convo_min_mins" not in st.session_state: st.session_state["convo_min_mins"] = 5
        if "convo_min_messages" not in st.session_state: st.session_state["convo_min_messages"] = 3
        if "join_likes_comments" not in st.session_state: st.session_state["join_likes_comments"] = False
        
        def sync_from_tab1():
            st.session_state["convo_min_mins"] = st.session_state["convo_min_mins_tab1"]
            st.session_state["convo_min_messages"] = st.session_state["convo_min_messages_tab1"]
            st.session_state["join_likes_comments"] = st.session_state["join_likes_comments_tab1"]
            st.session_state["convo_min_mins_tab2"] = st.session_state["convo_min_mins"]
            st.session_state["convo_min_messages_tab2"] = st.session_state["convo_min_messages"]
            st.session_state["join_likes_comments_tab2"] = st.session_state["join_likes_comments"]
        
        def sync_from_tab2():
            st.session_state["convo_min_mins"] = st.session_state["convo_min_mins_tab2"]
            st.session_state["convo_min_messages"] = st.session_state["convo_min_messages_tab2"]
            st.session_state["join_likes_comments"] = st.session_state["join_likes_comments_tab2"]
            st.session_state["convo_min_mins_tab1"] = st.session_state["convo_min_mins"]
            st.session_state["convo_min_messages_tab1"] = st.session_state["convo_min_messages"]
            st.session_state["join_likes_comments_tab1"] = st.session_state["join_likes_comments"]
        
        # seed per-tab widget state once
        if "convo_min_mins_tab1" not in st.session_state:
            st.session_state["convo_min_mins_tab1"] = st.session_state["convo_min_mins"]
            st.session_state["convo_min_messages_tab1"] = st.session_state["convo_min_messages"]
            st.session_state["join_likes_comments_tab1"] = st.session_state["join_likes_comments"]
            st.session_state["convo_min_mins_tab2"] = st.session_state["convo_min_mins"]
            st.session_state["convo_min_messages_tab2"] = st.session_state["convo_min_messages"]
            st.session_state["join_likes_comments_tab2"] = st.session_state["join_likes_comments"]










        
        with tab1:
            st.header(var.tab_engagement_funnel)
            st.caption("**Shows how interactions flow from starting point to deeper engagement, step by step**")
            st.divider()
            st.markdown(help_guide_direct, unsafe_allow_html=True)
            
            join_likes_comments = st.checkbox("Join comments & likes sent", key="join_likes_comments_tab1", on_change=sync_from_tab1)
            c1, c2 = st.columns(2)
            convo_min_mins = c1.number_input("Minimum conversation duration (min)", min_value=0, step=1, width="stretch", key="convo_min_mins_tab1", on_change=sync_from_tab1, help="Sets the minimum duration required for an interaction to count as a conversation.")
            convo_min_messages = c2.number_input("Minimum messages per conversation", min_value=0, step=1, width="stretch", key="convo_min_messages_tab1", on_change=sync_from_tab1, help="Sets the minimum number of messages required to count as a conversation.")
        
            sankey_data = ds.sankey_data(engagements, min_messages=convo_min_messages, min_minutes=convo_min_mins, join_comments_and_likes_sent=join_likes_comments)
            fig_sankey = viz.sankey(sankey_data, len(engagements))
            st.plotly_chart(fig_sankey, width="stretch")

            st.caption("Received likes only appear once they become matches.")
            st.caption("""
                My Type takes precedence over Blocks, which includes unmatches. If someone was marked as My Type and later blocked, they will still be counted as My Type.
            """)
            

            with st.expander("View as data"):
                st.dataframe(sankey_data, hide_index=True)









        
        with tab2:
            st.header(var.tab_engagement_over_time)
            st.caption("**Shows what happened in each time period, so you can spot trends**")
            st.divider()
            st.markdown(help_guide_direct, unsafe_allow_html=True)
            
            use_like_time = st.checkbox("Use like timestamp instead of event timestamp",
                                        help="""    
                                            Controls which timestamp is used to place events into time buckets.
                                            When enabled, events are grouped by when the like was sent or received.
                                            When disabled, events are grouped by when the event itself occurred (e.g., match, message).
                                            
                                            This answers two different questions:
                                            Using like time asks “How did my likes perform by when they were sent?”
                                            Using event time asks “What happened in each time period?”
                                        """)
            
            join_likes_comments = st.checkbox("Join comments & likes sent", key="join_likes_comments_tab2", on_change=sync_from_tab2)
            c1, c2 = st.columns(2)
            convo_min_mins = c1.number_input("Minimum conversation duration (min)", min_value=0, step=1, width="stretch", key="convo_min_mins_tab2", on_change=sync_from_tab2, help="Sets the minimum duration required for an interaction to count as a conversation.")
            convo_min_messages = c2.number_input("Minimum messages per conversation", min_value=0, step=1, width="stretch", key="convo_min_messages_tab2", on_change=sync_from_tab2, help="Sets the minimum number of messages required to count as a conversation.")
        
            engagements_over_time = ds.events_over_time_df(engagements, min_messages=convo_min_messages, min_minutes=convo_min_mins, join_comments_and_likes_sent=join_likes_comments, use_like_timestamp=use_like_time)

            
            fig_engagements_over_time, warning, output_df = viz.stacked_events_bar_fig(engagements_over_time)
            
            if fig_engagements_over_time is not None:
                st.plotly_chart(fig_engagements_over_time, use_container_width=True)
            if warning:
                st.caption(warning)  

            

            with st.expander("View as data"):
                output_df = output_df.set_index("Event")
                
                if join_likes_comments:
                    output_df = output_df.drop(index=["Comments", "Likes"], errors="ignore")
                else:
                    output_df = output_df.drop(index=["Comments & likes sent"], errors="ignore")

                
                st.dataframe(output_df)            




        

        with tab3:
            st.header(var.tab_outbound_timing)
            st.caption("**Highlights when outreach tends to perform best**")
            st.divider()
            st.markdown(help_guide_direct, unsafe_allow_html=True)
            
            st.caption("""
                        The score used below is more reliable than a raw match rate. A raw rate can be misleading with very little data, 
                        for example, 1 match from 2 likes doesn’t mean a time slot is better than one with 20 matches from 100 likes. 
                        This score reduces the impact of small samples so the results reflect real patterns
                    """)
            
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
                    "likes": "Comments & Likes",
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

            time_table = time_table.sort_values(["Score", "Comments & Likes"], ascending=[False, True])
            day_table = day_table.sort_values(["Score", "Comments & Likes"], ascending=[False, True])


            

            def fmt_pct(x):
                if x == 0:
                    return "0%"
                if x == 1:
                    return "100%"
                return f"{x:.1%}"
            
            day_table["Match Rate"] = day_table["Match Rate"].map(fmt_pct)
            time_table["Match Rate"] = time_table["Match Rate"].map(fmt_pct)
            day_time_table["Match Rate"] = day_time_table["Match Rate"].map(fmt_pct)

            day_table["Score"] = day_table["Score"].apply(lambda x: 0 if x == 0 else round(x, 1)) 
            time_table["Score"] = time_table["Score"].apply(lambda x: 0 if x == 0 else round(x, 1))          
            day_time_table["Score"] = day_time_table["Score"].apply(lambda x: 0 if x == 0 else round(x, 1))


            
            with st.expander("View as data"):
                time_table = time_table.set_index("Time Slot")
                st.dataframe(time_table)
                day_table = day_table.set_index("Day of Week")
                st.dataframe(day_table)
                st.dataframe(day_time_table, hide_index=True)
    
            




        
        with tab4:
            st.header(var.tab_drivers)
            st.caption("**Highlights what factors are most linked to higher messaging engagement**")
            st.divider()
            st.markdown(help_guide_direct, unsafe_allow_html=True)
            
            engagements.rename(columns={
                var.col_avg_message_gap: "Av. Time Between Messages (Mins)",
                var.col_first_message_delay: "Match to First Message Time (Mins)",
                var.col_conversation_message_count: "# of Messages per Session",
            }, inplace=True)
            
    
            columns_scatter = [
                "Match to First Message Time (Mins)",
                "Av. Time Between Messages (Mins)",
                "First Message: Time of Day",
                "First Message: Day of Week",
                "First Message: Daytime",
            ]
            
            colx = st.selectbox("Comparing", columns_scatter)
    
            
            fig = viz.scatter_plot(
                engagements,
                x_key=colx,
                y_col="# of Messages per Session",
                first_ts_col=var.col_first_message_timestamp,
                title="Messaging Analytics",
            )
            
            st.plotly_chart(fig, width="stretch")
    

            
            with st.expander("View as data"):
                out_df_drivers = engagements[[colx, "# of Messages per Session"]].set_index(colx).dropna()
                st.dataframe(out_df_drivers)
                
            # I know how this looks lol, shut up...
            engagements.rename(columns={
                "Av. Time Between Messages (Mins)": var.col_avg_message_gap,
                "Match to First Message Time (Mins)": var.col_first_message_delay,
                "# of Messages per Session": var.col_conversation_message_count,
            }, inplace=True)
     

        
        with tab5:
            st.header(var.tab_subscriptions)    
            st.caption("**Summarizes how your plan relates to activity and engagement**")
            st.divider()
            st.markdown(help_guide_direct, unsafe_allow_html=True)

            

        
        with tab6:

            st.header(var.tab_distribution)
            st.caption("**Shows how different metrics are spread out using box plots**")
            st.divider()
            st.markdown(help_guide_direct_w_box, unsafe_allow_html=True)
            
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

    
            mean_like_match_delay = int(engagements[var.col_like_match_delay].mean())
            fig_like_match_delay = viz.horizontal_boxplot(
                engagements[var.col_like_match_delay],
                title="Like to Match Time - Mean: {:,} Minutes".format(mean_like_match_delay),
                color = "#00CC96",
                trace_name="Minutes"
            )
    
            st.plotly_chart(fig_like_match_delay, width="stretch")



            with st.expander("View as data"):
                df_message_durations = pd.DataFrame(
                    {"Minutes": [engagements[var.col_conversation_span_minutes].dropna().tolist()]},
                    index=["Message Durations"],
                )
                
                df_messages_per_session = pd.DataFrame(
                    {"Messages": [engagements[var.col_conversation_message_count].dropna().tolist()]},
                    index=["Messages per Session"],
                )
                
                df_like_to_match_time = pd.DataFrame(
                    {"Minutes": [engagements[var.col_like_match_delay].dropna().tolist()]},
                    index=["Like to Match Time"],
                )
                
                # helpers
                fmt_1dp = lambda x: 0 if x == 0 else round(x, 1)
                fmt_int = lambda x: int(x)
                
                df_message_durations["Minutes"] = df_message_durations["Minutes"].apply(
                    lambda lst: sorted(fmt_1dp(v) for v in lst)
                )
                
                df_messages_per_session["Messages"] = df_messages_per_session["Messages"].apply(
                    lambda lst: sorted(fmt_int(v) for v in lst)
                )
                
                df_like_to_match_time["Minutes"] = df_like_to_match_time["Minutes"].apply(
                    lambda lst: sorted(fmt_1dp(v) for v in lst)
                )
                
                st.dataframe(df_message_durations)
                st.dataframe(df_messages_per_session)
                st.dataframe(df_like_to_match_time)



        

    


# if not logged in → show login screen
else:
    st.set_page_config(layout="centered")

    st.title("Unhinged")
    st.caption("**The post-mortem your dating life deserves**")

        
    



    tab1, tab2 = st.tabs(["Why", "Transparency"])


    with tab1:
        st.caption("""
            How you use a dating app affects your results. Sending likes or comments at the wrong times can reduce reach over time, even with a strong profile. This can leave you feeling...
            
            **Unhinged** helps you see what converts, what does not, and where effort is being wasted.
            The goal is better outcomes with less time and energy.
        """)

    with tab2:
        st.caption("""
            As more people opt in, we can share aggregate insights and percentiles based on real usage. Data is anonymized, shown only in aggregate, and stored securely. Anything useful we learn gets shared.
        """)
        
        st.caption("""
            **Unhinged** is open source and built in the open. Openness keeps things honest.
            
            The code is publicly available on GitHub so anyone can see how the app works and how data is processed. Individual user data is not visible.
        """)

    st.divider()
    auth.auth_screen()
    st.divider()


    
    
    theme = st_theme()
    base = (theme or {}).get("base", "dark")
    
    # flip it
    prefix = "light" if base == "dark" else "dark"

    
    imgs = [
        f"images/{prefix}_sankey.png",
        f"images/{prefix}_radial.png",
        f"images/{prefix}_stacked.png",
        f"images/{prefix}_box.png",
    ]
    
    c1, c2 = st.columns(2)
    with c1:
        st.image(imgs[0])
        st.image(imgs[2])
    with c2:
        st.image(imgs[1])
        st.image(imgs[3])



    
    st.divider()
    st.markdown("""
        **Notable limitations of Hinge data**:
        
        - The data only includes actions taken by you on Hinge. It does not include who you matched with, what they wrote, or whether someone unmatched or blocked you. Likes received are only visible when they result in a match.
        
        - Roses are not exposed separately in the data and appear the same as likes.
        
        - Timestamps do not include timezone information, so it is not possible to know whether messages were sent while either person was in a different timezone.
    """)
