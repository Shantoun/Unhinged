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
            import pandas as pd
            import plotly.graph_objects as go
        
            required = {"Source", "Target", "Value"}
            missing = required - set(sankey_df.columns)
            if missing:
                raise ValueError(f"sankey_df missing columns: {sorted(missing)}")
        
            df = sankey_df.copy()
            df["Source"] = df["Source"].astype(str)
            df["Target"] = df["Target"].astype(str)
            df["Value"] = pd.to_numeric(df["Value"], errors="coerce").fillna(0)
        
            df = df[df["Value"] > 0]
        
            labels = pd.Index(pd.concat([df["Source"], df["Target"]]).unique())
            label_to_idx = {label: i for i, label in enumerate(labels)}
        
            df["s_idx"] = df["Source"].map(label_to_idx)
            df["t_idx"] = df["Target"].map(label_to_idx)
        
            # totals for % math
            outflow = df.groupby("s_idx")["Value"].sum()  # total leaving each source node
            inflow = df.groupby("t_idx")["Value"].sum()   # total entering each target node
        
            # ---- link custom hover: % of previous (source) ----
            link_custom = []
            for s, t, v in zip(df["Source"], df["Target"], df["Value"]):
                s_i = label_to_idx[s]
                denom = float(outflow.get(s_i, 0.0))
                pct = (float(v) / denom) if denom else 0.0
                link_custom.append(f"{s} → {t}<br>{int(v)}<br>{pct:.1%} of {s}")
        
            # ---- node custom hover: show % of each immediate parent ----
            node_custom = [""] * len(labels)
            # build incoming link breakdown for each node
            incoming = df.groupby(["t_idx", "s_idx"])["Value"].sum().reset_index()
        
            for t_i in range(len(labels)):
                node_total = float(inflow.get(t_i, 0.0))
                if node_total == 0:
                    node_custom[t_i] = "0"
                    continue
        
                rows = incoming[incoming["t_idx"] == t_i]
                if rows.empty:
                    node_custom[t_i] = f"Total: {int(node_total)}"
                    continue
        
                lines = [f"Total: {int(node_total)}"]
                for _, r in rows.iterrows():
                    s_i = int(r["s_idx"])
                    v = float(r["Value"])
                    denom = float(outflow.get(s_i, 0.0))
                    pct = (v / denom) if denom else 0.0
                    lines.append(f"{labels[s_i]}: {pct:.1%}")
        
                node_custom[t_i] = "<br>".join(lines)
        
            fig = go.Figure(
                data=[
                    go.Sankey(
                        arrangement="snap",
                        node=dict(
                            label=labels.tolist(),
                            pad=18,
                            thickness=16,
                            customdata=node_custom,
                            hovertemplate="%{label}<br>%{customdata}<extra></extra>",
                        ),
                        link=dict(
                            source=df["s_idx"].tolist(),
                            target=df["t_idx"].tolist(),
                            value=df["Value"].astype(float).tolist(),
                            customdata=link_custom,
                            hovertemplate="%{customdata}<extra></extra>",
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
