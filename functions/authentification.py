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

def send_reset_email(email):
    """Send password reset email"""
    try:
        supabase.auth.reset_password_email(email)
        return True, "Password reset link sent! Check your email."
    except Exception as e:
        return False, f"Error: {e}"

def auth_screen():
    st.header("Login or Sign Up")
    
    # Toggle between login and reset
    if "show_reset" not in st.session_state:
        st.session_state.show_reset = False
    
    if not st.session_state.show_reset:
        # Normal login/signup
        email = st.text_input("Email")
        password = st.text_input("Password", type="password", help="Must be at least 8 characters")
        
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
        
        st.write("")
        if st.button("Forgot password?"):
            st.session_state.show_reset = True
            st.rerun()
    
    else:
        # Password reset form
        st.info("Enter your email to receive a password reset link")
        reset_email = st.text_input("Email")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Send Reset Link", type="primary", use_container_width=True):
                if reset_email:
                    success, msg = send_reset_email(reset_email)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.warning("Enter your email")
        
        with col2:
            if st.button("Back to Login", use_container_width=True):
                st.session_state.show_reset = False
                st.rerun()

def sign_out():
    supabase.auth.sign_out()
    st.session_state.user_email = None
    st.session_state.user_id = None 
    st.rerun()
