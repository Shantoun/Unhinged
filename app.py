import streamlit as st
import functions.authentification as auth
from functions.zip_uploader import uploader
import variables as var

# CRITICAL: Check for password reset tokens FIRST, before any auth checks
auth.check_for_reset_tokens()

# If we're in password reset mode, show that screen and stop
if st.session_state.get("password_reset_mode", False):
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
