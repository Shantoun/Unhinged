from supabase import create_client, Client
import streamlit as st
import streamlit.components.v1 as components

supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)

def check_for_reset_tokens():
    """Check if URL contains password reset tokens and extract them"""
    
    fragment_script = """
    <script>
        const hash = window.location.hash;
        if (hash && hash.includes('type=recovery')) {
            const params = new URLSearchParams(hash.substring(1));
            const accessToken = params.get('access_token');
            const refreshToken = params.get('refresh_token');
            const type = params.get('type');
            
            if (type === 'recovery' && accessToken && refreshToken) {
                const url = new URL(window.location.href);
                url.search = `?access_token=${accessToken}&refresh_token=${refreshToken}&type=recovery`;
                url.hash = '';
                window.location.href = url.toString();
            }
        }
    </script>
    """
    components.html(fragment_script, height=0)
    
    if st.query_params.get("type") == "recovery":
        access_token = st.query_params.get("access_token")
        refresh_token = st.query_params.get("refresh_token")
        
        if access_token and refresh_token:
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
        redirect_url = st.secrets.get("APP_URL", "http://localhost:8501")
        supabase.auth.reset_password_email(email, options={"redirect_to": redirect_url})
        return True, "Check your email for a password reset link"
    except Exception as e:
        return False, f"Error sending reset email: {e}"

def password_reset_screen():
    """Screen for resetting password after clicking email link"""
    st.header("Reset Your Password")
    
    access_token = st.session_state.get("reset_access_token")
    refresh_token = st.session_state.get("reset_refresh_token")
    
    if not access_token or not refresh_token:
        st.error("Invalid or expired reset link. Please request a new one.")
        if st.button("Back to Login"):
            # CLEAR EVERYTHING
            for key in ["password_reset_mode", "reset_access_token", "reset_refresh_token", "recovery_session_set"]:
                st.session_state.pop(key, None)
            st.query_params.clear()
            st.rerun()
        return
    
    try:
        if "recovery_session_set" not in st.session_state:
            supabase.auth.set_session(access_token, refresh_token)
            st.session_state.recovery_session_set = True
    except Exception as e:
        st.error(f"Error setting session: {e}")
        if st.button("Back to Login"):
            for key in ["password_reset_mode", "reset_access_token", "reset_refresh_token", "recovery_session_set"]:
                st.session_state.pop(key, None)
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
                supabase.auth.update_user({"password": new_password})
                st.success("Password updated successfully!")
                
                # CLEAR EVERYTHING
                for key in ["password_reset_mode", "reset_access_token", "reset_refresh_token", "recovery_session_set"]:
                    st.session_state.pop(key, None)
                st.query_params.clear()
                supabase.auth.sign_out()
                
                import time
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Error updating password: {e}")
        else:
            st.warning("Please enter and confirm your new password")

def auth_screen():
    if st.session_state.get("password_reset_mode", False):
        password_reset_screen()
        return
    
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
    for key in ["password_reset_mode", "reset_access_token", "reset_refresh_token", "recovery_session_set"]:
        st.session_state.pop(key, None)
    st.rerun()
