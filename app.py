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
    # Sign out
    if st.sidebar.button("Sign Out", width="stretch"):
        auth.sign_out()
        st.rerun()

    
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
        if st.button("Upload Data"):
            hinge_sync_dialog()
            
    # # --- MAIN APP LOGIC ---
    # uploader()



# if not logged in → show login screen
else:
    auth.auth_screen()






# def main_app(user_email):
#     st.set_page_config(layout="wide")
#     st.title("Unhinged")
#     st.caption("Analyze your game")
    
#     with st.sidebar:
#         if st.button("Sign Out", width="stretch"):
#             auth.sign_out()

    



# if "user_email" not in st.session_state:
#     st.session_state.user_email = None

# if st.session_state.user_email:
#     main_app(st.session_state.user_email)
# else:
#     auth.auth_screen()
