import streamlit as st
from supabase import create_client, Client

# Initialize client
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)


# -------------------- SMART AUTH --------------------
def smart_auth(email, password):
    """Try login first, if it fails try signup automatically."""
    try:
        user = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return user, "success", "Welcome back!"
    except:
        try:
            user = supabase.auth.sign_up({"email": email, "password": password})
            if user and user.user:
                if user.user.email_confirmed_at is None:
                    return None, "check_email", f"Check your email ({email}) to confirm your account."
                return user, "success", "Account created!"
        except Exception as e:
            if "already registered" in str(e).lower():
                return None, "error", "Wrong password."
            return None, "error", f"Error: {e}"

    return None, "error", "Authentication failed."


# -------------------- AUTH SCREEN --------------------
def auth_screen():
    st.header("Login or Sign Up")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    # ------- Continue Button -------
    if st.button("Continue", type="primary", use_container_width=True):
        if email and password:
            user, status, msg = smart_auth(email, password)

            if status == "success":
                st.session_state.user_email = user.user.email
                st.session_state.user_id = user.user.id
                st.success(msg)
                st.rerun()

            elif status == "check_email":
                st.info(msg)
            else:
                st.error(msg)
        else:
            st.warning("Enter email and password")

    # ------- Forgot Password (link style button) -------
    st.markdown("""
        <style>
        button[kind="secondary"] {
            background: none !important;
            border: none !important;
            box-shadow: none !important;
            padding-left: 0px !important;
            text-align: left !important;
            color: #4B9CFF !important;
            text-decoration: underline !important;
        }
        </style>
    """, unsafe_allow_html=True)

    if st.button("Forgot password?", key="forgot_pw", type="secondary"):
        if email:
            supabase.auth.reset_password_for_email(
                email,
                options={"redirect_to": "https://unhinged.streamlit.app/reset_password"} # <- Your reset page
            )
            st.success(f"Reset link sent to {email}")
        else:
            st.warning("Enter your email to reset your password")


# -------------------- SIGN OUT --------------------
def sign_out():
    supabase.auth.sign_out()
    st.session_state.user_email = None
    st.session_state.user_id = None
    st.rerun()
