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
    """Send password reset email"""
    try:
        # Get your app's URL
        redirect_url = st.secrets.get("APP_URL", "http://localhost:8501")
        
        supabase.auth.reset_password_email(
            email,
            options={"redirect_to": redirect_url}
        )
        return True, "Check your email for a password reset link"
    except Exception as e:
        return False, f"Error sending reset email: {e}"

def password_reset_screen():
    """Screen for resetting password after clicking email link"""
    st.header("Reset Your Password")
    
    # Get tokens from session state
    access_token = st.session_state.get("reset_access_token")
    refresh_token = st.session_state.get("reset_refresh_token")
    
    if not access_token or not refresh_token:
        st.error("Invalid or expired reset link. Please request a new one.")
        if st.button("Back to Login"):
            st.session_state.password_reset_mode = False
            st.session_state.pop("reset_access_token", None)
            st.session_state.pop("reset_refresh_token", None)
            st.query_params.clear()
            st.rerun()
        return
    
    # Set the session with the recovery tokens
    try:
        if "recovery_session_set" not in st.session_state:
            st.info("Setting up session...")
            supabase.auth.set_session(access_token, refresh_token)
            st.session_state.recovery_session_set = True
            st.success("Session verified. Please enter your new password.")
    except Exception as e:
        st.error(f"Error setting session: {e}")
        st.code(f"Access token: {access_token[:20]}...")
        if st.button("Back to Login"):
            st.session_state.password_reset_mode = False
            st.session_state.pop("reset_access_token", None)
            st.session_state.pop("reset_refresh_token", None)
            st.session_state.pop("recovery_session_set", None)
            st.query_params.clear()
            st.rerun()
        return
    
    new_password = st.text_input("New Password", type="password", help="Must be at least 8 characters")
    confirm_password = st.text_input("Confirm New Password", type="password")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("Reset Password", type="primary", use_container_width=True):
            if new_password and confirm_password:
                if new_password != confirm_password:
                    st.error("Passwords don't match")
                    return
                
                if len(new_password) < 8:
                    st.error("Password must be at least 8 characters")
                    return
                
                try:
                    # Update the password
                    result = supabase.auth.update_user({"password": new_password})
                    st.success("Password updated successfully! You can now log in with your new password.")
                    
                    # Clear everything
                    st.session_state.password_reset_mode = False
                    st.session_state.pop("recovery_session_set", None)
                    st.session_state.pop("reset_access_token", None)
                    st.session_state.pop("reset_refresh_token", None)
                    st.query_params.clear()
                    
                    # Sign out to clear the recovery session
                    supabase.auth.sign_out()
                    
                    # Wait a moment before rerunning
                    import time
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating password: {e}")
            else:
                st.warning("Please enter and confirm your new password")
    
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.session_state.password_reset_mode = False
            st.session_state.pop("recovery_session_set", None)
            st.session_state.pop("reset_access_token", None)
            st.session_state.pop("reset_refresh_token", None)
            st.query_params.clear()
            st.rerun()

def auth_screen():
    # Check if we're in password reset mode
    if st.session_state.get("password_reset_mode", False):
        password_reset_screen()
        return
    
    st.header("Login or Sign Up")
    
    # Main login form
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
    
    # Forgot password section
    st.divider()
    
    with st.expander("🔐 Forgot your password?"):
        st.write("Enter your email address and we'll send you a link to reset your password.")
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
    # Also clear any reset-related state
    st.session_state.pop("password_reset_mode", None)
    st.session_state.pop("reset_access_token", None)
    st.session_state.pop("reset_refresh_token", None)
    st.session_state.pop("recovery_session_set", None)
    st.rerun()
