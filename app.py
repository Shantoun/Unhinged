import streamlit as st
import functions.authentification as auth
from main import main


main()

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
