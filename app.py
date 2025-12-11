import streamlit as st
import functions.authentification as auth
from functions.zip_uploader import uploader
import variables as var

# ---- MUST BE FIRST: Recovery Mode Check ----
session = auth.supabase.auth.get_session()
if session and session.get("type") == "recovery":
    from pages.reset_password import reset_password_screen
    reset_password_screen()
    st.stop()



# ---- initialize user_id ----
if var.col_user_id not in st.session_state:
    st.session_state.user_id = None

user_id = st.session_state.user_id


# ---- if logged in → main app ----
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

    if st.sidebar.button("Sign Out", width="stretch"):
        auth.sign_out()
        st.rerun()


# ---- if not logged in → login screen ----
else:
    auth.auth_screen()
