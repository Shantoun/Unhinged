from functions.authentification import supabase
import streamlit as st
import functions.authentification as auth
from functions.zip_uploader import uploader
import variables as var


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
            

        
        import streamlit as st
        import pandas as pd
        import plotly.graph_objects as go
        
        # ---------- helpers ----------
        def fetch_df(table, user_id):
            res = (
                supabase
                .table(table)
                .select("*")
                .eq("user_id", user_id)
                .execute()
            )
            return pd.DataFrame(res.data or [])
        
        def sankey(data):
            nodes = pd.unique(data[["source", "target"]].values.ravel())
            idx = {n: i for i, n in enumerate(nodes)}
        
            fig = go.Figure(
                go.Sankey(
                    arrangement="snap",
                    node=dict(label=list(nodes), pad=15, thickness=20),
                    link=dict(
                        source=data["source"].map(idx),
                        target=data["target"].map(idx),
                        value=data["value"],
                    ),
                )
            )
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            return fig
        
        def build_sankey_data(
            likes_df,
            matches_df,
            messages_df,
            blocks_df,
            combine_likes=False,
            min_messages=3,
            min_span_minutes=5,
        ):
            rows = []
        
            # like has comment if any message references like_id
            comments = (
                messages_df[messages_df["like_id"].notna()][["like_id"]]
                .drop_duplicates()
                .assign(has_comment=True)
            )
            likes = likes_df.merge(comments, on="like_id", how="left")
            likes["has_comment"] = likes["has_comment"].fillna(False)
        
            # initiator: first message before match_timestamp => them
            first_msg = (
                messages_df.groupby("match_id")["message_timestamp"]
                .min()
                .reset_index(name="first_message_ts")
            )
            matches = matches_df.merge(first_msg, on="match_id", how="left")
            matches["initiator"] = "you"
            matches.loc[
                (matches["first_message_ts"].notna())
                & (matches["first_message_ts"] < matches["match_timestamp"]),
                "initiator",
            ] = "them"
        
            # conversation rule
            convo_stats = (
                messages_df.groupby("match_id")
                .agg(
                    message_count=("message_id", "count"),
                    span_minutes=(
                        "message_timestamp",
                        lambda x: (x.max() - x.min()).total_seconds() / 60,
                    ),
                )
                .reset_index()
            )
            convo_ids = set(
                convo_stats[
                    (convo_stats["message_count"] >= min_messages)
                    & (convo_stats["span_minutes"] >= min_span_minutes)
                ]["match_id"]
            )
        
            blocked_ids = set(blocks_df["match_id"].dropna().unique())
        
            for _, like in likes.iterrows():
                entry = (
                    "Likes sent"
                    if combine_likes
                    else ("Likes (with comment)" if like["has_comment"] else "Likes (no comment)")
                )
        
                if pd.isna(like["match_id"]):
                    continue
        
                m = matches[matches["match_id"] == like["match_id"]]
                if m.empty:
                    continue
                m = m.iloc[0]
        
                match_node = (
                    "Matched (initiated by them)"
                    if m["initiator"] == "them"
                    else "Matched (initiated by you)"
                )
        
                rows.append((entry, match_node))
        
                if like["match_id"] in blocked_ids:
                    rows.append((match_node, "Blocked / Removed"))
                    continue
        
                if like["match_id"] in convo_ids:
                    rows.append((match_node, "Conversation"))
        
                    if bool(m.get("we_met")):
                        rows.append(("Conversation", "We met"))
                        rows.append(
                            ("We met", "My type" if bool(m.get("my_type")) else "Not my type")
                        )
        
            data = (
                pd.DataFrame(rows, columns=["source", "target"])
                .value_counts()
                .reset_index(name="value")
            )
            return data
        
        @st.cache_data(show_spinner=False)
        def load_and_build(user_id, combine_likes, min_messages, min_span_minutes):
            likes_df = fetch_df("likes", user_id)
            matches_df = fetch_df("matches", user_id)
            messages_df = fetch_df("messages", user_id)
            blocks_df = fetch_df("blocks", user_id)
        
            return build_sankey_data(
                likes_df,
                matches_df,
                messages_df,
                blocks_df,
                combine_likes,
                min_messages,
                min_span_minutes,
            )
        
        # ---------- UI ----------
        combine_likes = st.checkbox("Combine likes")
        min_messages = st.slider("Min messages", 1, 10, 3)
        min_span_minutes = st.slider("Min span (minutes)", 1, 60, 5)
        
        data = load_and_build(user_id, combine_likes, min_messages, min_span_minutes)
        st.plotly_chart(sankey(data), use_container_width=True)








    



    
    # Sign out
    if st.sidebar.button("Sign Out", width="stretch"):
        auth.sign_out()
        st.rerun()


# if not logged in → show login screen
else:
    auth.auth_screen()
