import streamlit as st
from functions.authentification import supabase


def reset_password_screen():
    st.header("Reset Your Password")

    session = supabase.auth.get_session()

    # User reached here from Supabase magic link
    if session and session.get("type") == "recovery":
        new_pw = st.text_input("New Password", type="password")

        if st.button("Update Password", type="primary"):
            try:
                supabase.auth.update_user({"password": new_pw})
                st.success("Password updated! Please log in again.")
                st.session_state.clear()
                st.rerun()
            except Exception as e:
                st.error(str(e))
    else:
        st.error("Invalid or expired reset link.")


reset_password_screen()
