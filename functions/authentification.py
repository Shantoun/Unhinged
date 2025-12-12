from supabase import create_client, Client
import streamlit as st

supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)

def smart_auth(email, password):
    """Try login first, if it fails try signup"""
    try:
        user = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return user, "success", "Welcome back!"
    except:
        try:
            user = supabase.auth.sign_up({"email": email, "password": password})
            if user and user.user:
                if user.user.email_confirmed_at is None:
                    return None, "check_email", f"Check your email ({email}) to confirm your account, then log in again."
                return user, "success", "Account created!"
        except Exception as e:
            if "already registered" in str(e).lower():
                return None, "error", "Wrong password."
            return None, "error", f"Error: {e}"
    return None, "error", "Authentication failed."

def reset_password(email):
    """Send password reset email with proper redirect"""
    try:
        # Point to the HTML redirect page that converts hash to query params
        redirect_to = "https://unhinged.streamlit.app/reset_redirect.html"
        
        supabase.auth.reset_password_email(email, options={"redirect_to": redirect_to})
        return True, "Password reset email sent! Check your inbox."
    except Exception as e:
        return False, f"Error: {e}"

def auth_screen():
    st.header("Login or Sign Up")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password", help="Must be at least 8 characters")
    
    col1, col2 = st.columns([3, 1])
    with col1:
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
    
    with col2:
        if st.button("Forgot password?", use_container_width=True):
            if email:
                success, msg = reset_password(email)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.warning("Enter your email first")

def sign_out():
    supabase.auth.sign_out()
    st.session_state.user_email = None
    st.session_state.user_id = None 
    st.rerun()
