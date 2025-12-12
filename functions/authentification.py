from supabase import create_client, Client
import streamlit as st
import streamlit.components.v1 as components

supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)

def check_for_reset_tokens():
    """Check if URL contains password reset tokens and extract them"""
    
    # Use a hidden component to extract fragment data
    fragment_script = """
    <script>
        const hash = window.location.hash;
        if (hash) {
            const params = new URLSearchParams(hash.substring(1));
            const accessToken = params.get('access_token');
            const refreshToken = params.get('refresh_token');
            const type = params.get('type');
            
            if (type === 'recovery' && accessToken && refreshToken) {
                // Redirect to query params so Streamlit can see them
                const url = new URL(window.location.href);
                url.search = `?access_token=${accessToken}&refresh_token=${refreshToken}&type=recovery`;
                url.hash = '';
                window.location.href = url.toString();
            }
        }
    </script>
    """
    components.html(fragment_script, height=0)
    
    # Now check query params
    if st.query_params.get("type") == "recovery":
        access_token = st.query_params.get("access_token")
        refresh_token = st.query_params.get("refresh_token")
        
        if access_token and refresh_token:
            # Store in session state
            st.session_state.reset_access_token = access_token
            st.session_state.reset_refresh_token = refresh_token
            st.session_state.password_reset_mode = True

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
            st.query_params.clear()
            st.rerun()
        return
    
    # Set the session with the recovery tokens
    try:
        if "recovery_session_set" not in st.session_state:
            supabase.auth.set_session(access_token, refresh_token)
            st.session_state.recovery_session_set = True
            st.success("Session verified. Please enter your new password.")
    except Exception as e:
        st.error(f"Error setting session: {e}")
        if st.button("Back to Login"):
            st.session_state.password_reset_mode = False
            st.session_state.pop("reset_access_token", None)
            st.session_state.pop("reset_refresh_token", None)
            st.query_params.clear()
            st.rerun()
        return
    
    new_password = st.text_input("New Password", type="password", help="Must be at least 8 characters")
    confirm_password = st.text_input("Confirm New Password", type="password")
    
    if st.button("Reset Password", type="primary"):
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
    
    if st.button("Cancel"):
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
    
    # Forgot password link
