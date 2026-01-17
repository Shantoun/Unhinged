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



        def sankey(sankey_df):
            title = "Engagement Funnel: {} Total Engagements".format(len(sankey_df))
        
            required = {"Source", "Target", "Value"}
            missing = required - set(sankey_df.columns)
            if missing:
                raise ValueError(f"sankey_df missing columns: {sorted(missing)}")
        
            df = sankey_df.copy()
            df["Source"] = df["Source"].astype(str)
            df["Target"] = df["Target"].astype(str)
            df["Value"] = pd.to_numeric(df["Value"], errors="coerce").fillna(0.0)
        
            df = df[df["Value"] > 0]
        
            labels = pd.Index(pd.concat([df["Source"], df["Target"]]).unique())
            label_to_idx = {label: i for i, label in enumerate(labels)}
        
            df["s_idx"] = df["Source"].map(label_to_idx)
            df["t_idx"] = df["Target"].map(label_to_idx)
        
            # totals
            outflow = df.groupby("s_idx")["Value"].sum()
            inflow = df.groupby("t_idx")["Value"].sum()
        
            # node "value" = max(inflow, outflow) (this fixes your 2/3 = 66.7% case)
            node_value = {
                i: float(max(inflow.get(i, 0.0), outflow.get(i, 0.0)))
                for i in range(len(labels))
            }
        
            def pct_of_prev(v, prev_idx):
                denom = node_value.get(prev_idx, 0.0)
                return (float(v) / denom) if denom else 0.0
        
            def left_html(s):
                return f"<span style='display:block;text-align:left;'>{s}</span>"
        
            # ---- link hover: value + % of previous (source node total) ----
            link_custom = []
            for s_i, t_i, v in zip(df["s_idx"], df["t_idx"], df["Value"]):
                s_label = labels[int(s_i)]
                t_label = labels[int(t_i)]
                pct = pct_of_prev(v, int(s_i))
                txt = f"{s_label} → {t_label}<br>{int(v)}<br>{pct:.1%} of {s_label}"
                link_custom.append(left_html(txt))
        
            # ---- node hover: total + % of each immediate parent ----
            incoming = df.groupby(["t_idx", "s_idx"])["Value"].sum().reset_index()
            node_custom = [""] * len(labels)
        
            for t_i in range(len(labels)):
                total = node_value.get(t_i, 0.0)
                if total == 0:
                    node_custom[t_i] = left_html("0")
                    continue
        
                rows = incoming[incoming["t_idx"] == t_i]
                if rows.empty:
                    node_custom[t_i] = left_html(f"Total: {int(total)}")
                    continue
        
                lines = [f"Total: {int(total)}"]
                for _, r in rows.iterrows():
                    s_i = int(r["s_idx"])
                    v = float(r["Value"])
                    pct = pct_of_prev(v, s_i)
                    lines.append(f"{pct:.1%} of {labels[s_i]}")
        
                node_custom[t_i] = left_html("<br>".join(lines))
        
            fig = go.Figure(
                data=[
                    go.Sankey(
                        arrangement="snap",
                        node=dict(
                            label=labels.tolist(),
                            pad=18,
                            thickness=16,
                            customdata=node_custom,
                            hovertemplate="%{customdata}<extra></extra>",
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
