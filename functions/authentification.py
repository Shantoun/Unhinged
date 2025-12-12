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

def send_password_reset(email):
    """Send password reset email - user resets on Supabase's hosted page"""
    try:
        supabase.auth.reset_password_email(email)
        return True, "Check your email for a password reset link"
    except Exception as e:
        return False, f"Error: {e}"

def auth_screen():
    st.header("Login or Sign Up")
    
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", help="Must be at least 8 characters", key="login_password")
    
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
    
    st.divider()
    
    with st.expander("🔐 Forgot your password?"):
        st.write("Enter your email and we'll send you a secure link to reset your password.")
        forgot_email = st.text_input("Email address", key="forgot_email")
        
        if st.button("Send Reset Link", use_container_width=True):
            if forgot_email:
                success, message = send_password_reset(forgot_email)
                if success:
                    st.success(message)
                else:
                    st.error(message)
            else:
                st.warning("Please enter your email address")

def sign_out():
    supabase.auth.sign_out()
    st.session_state.user_email = None
    st.session_state.user_id = None
    st.rerun()
