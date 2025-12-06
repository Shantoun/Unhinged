import streamlit as st
from supabase import create_client, Client

# --- Supabase Init ---
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)

# --- OAuth Redirect Handler (must run before UI) ---
session = supabase.auth.get_session()
if session and session.user:
    st.session_state.user_email = session.user.email


# --- Auth Functions ---
def sign_up(email, password):
    try:
        return supabase.auth.sign_up({"email": email, "password": password})
    except Exception as e:
        st.error(f"Registration failed: {e}")


def sign_in(email, password):
    try:
        return supabase.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as e:
        st.error(f"Login failed: {e}")


def sign_in_google():
    try:
        res = supabase.auth.sign_in_with_oauth({"provider": "google"})
        oauth_url = res.url

        # same-tab redirect to avoid new Streamlit session
        st.write(
            f'<script>window.location.href = "{oauth_url}";</script>',
            unsafe_allow_html=True
        )

    except Exception as e:
        st.error(f"Google login failed: {e}")


def sign_out():
    try:
        supabase.auth.sign_out()
        st.session_state.user_email = None
        st.rerun()
    except Exception as e:
        st.error(f"Logout failed: {e}")


# --- Main App ---
def main_app(user_email):
    st.title("🎉 Welcome Page")
    st.success(f"Welcome, {user_email}!")
    if st.button("Logout"):
        sign_out()


# --- Auth Screen ---
def auth_screen():
    st.title("🔐 Streamlit & Supabase Auth App")

    option = st.selectbox("Choose an action:", ["Login", "Sign Up"])
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    # Sign Up
    if option == "Sign Up" and st.button("Register"):
        user = sign_up(email, password)
        if user and user.user:
            st.success("Registration successful. Please log in.")

    # Log In
    if option == "Login" and st.button("Login"):
        user = sign_in(email, password)
        if user and user.user:
            st.session_state.user_email = user.user.email
            st.rerun()

    st.divider()
    st.write("Or")

    if st.button("Sign in with Google"):
        sign_in_google()


# --- Session Init ---
if "user_email" not in st.session_state:
    st.session_state.user_email = None


# --- Routing ---
if st.session_state.user_email:
    main_app(st.session_state.user_email)
else:
    auth_screen()
