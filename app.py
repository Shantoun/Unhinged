import streamlit as st
import functions.authentification as auth
from functions.zip_uploader import uploader
import functions.supabase_ingest as ingest


# initialize the key so it always exists
if "user_id" not in st.session_state:
    st.session_state.user_id = None


# if logged in → main app
if st.session_state.user_id:

    # SIGN OUT FIRST — always evaluated before anything else
    if st.sidebar.button("Sign Out", width="stretch"):
        auth.sign_out()
        st.rerun()

    # --- MAIN APP LOGIC ---
    result = uploader()

    if result:
        json_data = result["json"]

        with st.spinner("Uploading likes..."):
            ingest.likes_ingest(json_data, st.session_state.user_id)

        with st.spinner("Uploading matches..."):
            ingest.matches_ingest(json_data, st.session_state.user_id)

        with st.spinner("Uploading messages..."):
            ingest.messages_ingest(json_data, st.session_state.user_id)        
        
        with st.spinner("Uploading blocks..."):
            ingest.blocks_ingest(json_data, st.session_state.user_id)

        with st.spinner("Uploading user info..."):
            ingest.user_profile_ingest(json_data, st.session_state.user_id)
            ingest.media_ingest(json_data, st.session_state.user_id)
            ingest.prompts_ingest(json_data, st.session_state.user_id)
            ingest.subscriptions_ingest(json_data, st.session_state.user_id)

        st.success("Your data has been uploaded")


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
