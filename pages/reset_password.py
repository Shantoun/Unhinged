import streamlit as st
from functions.authentification import supabase

st.set_page_config(page_title="reset_password")

def reset_password_screen():
    st.header("Reset Your Password")

    session = supabase.auth.get_session()

    if session and session.get("type") == "recovery":
        new_pw = st.text_input("New Password", type="password")

        if st.button("Update Password", type="primary"):
            supabase.auth.update_user({"password": new_pw})
            st.success("Password updated! Please log in again.")
            st.session_state.clear()
            st.rerun()
    else:
        st.error("Invalid or expired reset link.")

reset_password_screen()
