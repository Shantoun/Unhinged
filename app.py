from functions.authentification import supabase
import streamlit as st
import functions.authentification as auth
from functions.zip_uploader import uploader
import variables as var

import pandas as pd
import plotly.graph_objects as go

import functions.datasets as ds



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
            

        df = ds.like_events_df(user_id)
        st.write(df)


            
        
        sankey_data = ds.sankey_data(df)
        
        st.write(sankey_data)



        def sankey(sankey_df, title="Unhinged funnel"):
            import plotly.graph_objects as go
            import pandas as pd
        
            # expects columns: Source, Target, Value
            required = {"Source", "Target", "Value"}
            missing = required - set(sankey_df.columns)
            if missing:
                raise ValueError(f"sankey_df missing columns: {sorted(missing)}")
        
            df = sankey_df.copy()
            df["Source"] = df["Source"].astype(str)
            df["Target"] = df["Target"].astype(str)
            df["Value"] = pd.to_numeric(df["Value"], errors="coerce").fillna(0).astype(int)
        
            # drop zeros just in case
            df = df[df["Value"] > 0]
        
            labels = pd.Index(pd.concat([df["Source"], df["Target"]]).unique())
            label_to_idx = {label: i for i, label in enumerate(labels)}
        
            source_idx = df["Source"].map(label_to_idx).tolist()
            target_idx = df["Target"].map(label_to_idx).tolist()
            values = df["Value"].tolist()
        
            fig = go.Figure(
                data=[
                    go.Sankey(
                        arrangement="snap",
                        node=dict(
                            label=labels.tolist(),
                            pad=18,
                            thickness=16,
                        ),
                        link=dict(
                            source=source_idx,
                            target=target_idx,
                            value=values,
                        ),
                    )
                ]
            )
        
            fig.update_layout(title_text=title, height=520, margin=dict(l=10, r=10, t=50, b=10))
            return fig



        fig = sankey(sankey_data)
        st.plotly_chart(fig, use_container_width=True)



    

    
    # Sign out
    if st.sidebar.button("Sign Out", width="stretch"):
        auth.sign_out()
        st.rerun()


# if not logged in → show login screen
else:
    auth.auth_screen()
