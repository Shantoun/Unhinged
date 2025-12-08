# import streamlit as st

# if not st.user.is_logged_in:
#     st.write("Not logged in")
#     if st.button("Sign in with Google"):
#         st.login("google")
# else:
#     st.write(f"User: {st.user.name}")
#     st.write(f"Email: {st.user.email}")
#     st.success("Logged in")
    
#     if st.button("Sign out"):
#         st.logout()
import streamlit as st
import functions.authentification as auth


def main_app(user_email):
    st.title("🎉 Welcome")
    st.success(f"Welcome, {user_email}!")
    if st.button("Logout"):
        supabase.auth.sign_out()
        st.session_state.user_email = None
        st.rerun()

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if st.session_state.user_email:
    main_app(st.session_state.user_email)
else:
    auth.auth_screen()
