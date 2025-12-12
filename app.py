import streamlit as st
import functions.authentification as auth
from functions.zip_uploader import uploader
import variables as var

# Check if this is a password reset callback first
# Supabase adds fragment params like #access_token=...&type=recovery
if st.query_params.get("type") == "recovery" or "recovery" in st.query_params.to_dict().get("type", ""):
    auth.password_reset_screen()
    st.stop()

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
        if st.sidebar.button("Upload Data", use_container_width=True):
            hinge_sync_dialog()
    
    # Sign out
    if st.sidebar.button("Sign Out", use_container_width=True):
        auth.sign_out()
        st.rerun()

# if not logged in → show login screen
else:
    auth.auth_screen()
