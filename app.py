
import streamlit as st
import functions.authentification as auth


def main_app(user_email):
    st.title("🎉 Welcome")
    st.success(f"Welcome, {user_email}!")
    if st.button("Logout"):
        auth.sign_out()

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if st.session_state.user_email:
    main_app(st.session_state.user_email)
else:
    auth.auth_screen()
