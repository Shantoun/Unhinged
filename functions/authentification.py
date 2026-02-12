from supabase import create_client, Client
import streamlit as st

supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)
supabase_admin: Client = create_client(
    supabase_url,
    st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
)

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
                    return None, "check_email", (
                        "If this is a new account, check your email to confirm it. "
                        "Otherwise, the email or password is incorrect."
                    )
                return user, "success", "Account created!"
        except Exception as e:
            if "already registered" in str(e).lower():
                return None, "error", "Wrong password."
            return None, "error", f"Error: {e}"
    return None, "error", "Authentication failed."

def request_password_reset(email):
    """Send password reset email with 6-digit code"""
    try:
        supabase.auth.reset_password_email(email)
        return True, "Check your email for a 6-digit code"
    except Exception as e:
        return False, f"Error: {e}"

def verify_and_reset_password(email, token, new_password):
    """Verify the code and reset password"""
    try:
        # Verify OTP and get session
        response = supabase.auth.verify_otp({
            'email': email,
            'token': token,
            'type': 'recovery'
        })
        
        # Update password
        supabase.auth.update_user({"password": new_password})
        return True, "Password reset successful!"
        
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid" in error_msg or "expired" in error_msg:
            return False, "Invalid or expired code. Request a new one."
        return False, f"Error: {e}"

def auth_screen():
    st.header("Login or Sign Up")
    
    # Initialize reset mode
    if 'reset_mode' not in st.session_state:
        st.session_state.reset_mode = False
    
    if not st.session_state.reset_mode:
        # Normal login/signup
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", 
                                help="Must be at least 8 characters", 
                                key="login_password")
        
        if st.button("Continue", type="primary"):
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
        
        # Forgot password expander
        with st.expander("🔑 Forgot Password?"):
            st.write("Enter your email and we'll send you a 6-digit code")
            
            reset_email = st.text_input("Email Address", key="reset_email_input")
            
            if st.button("Send Reset Code", type="secondary"):
                if reset_email:
                    success, msg = request_password_reset(reset_email)
                    if success:
                        st.success(msg)
                        st.session_state.reset_mode = True
                        st.session_state.reset_email = reset_email
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Please enter your email")
    
    else:
        # Password reset screen
        st.subheader("Enter Reset Code")
        
        email = st.session_state.get('reset_email', '')
        st.info(f"📧 Code sent to: **{email}**")
        st.caption("Check your email (and spam folder)")
        
        token = st.text_input("6-Digit Code", 
                             max_chars=6, 
                             key="reset_token",
                             placeholder="123456")
        
        new_password = st.text_input("New Password", 
                                     type="password", 
                                     help="Must be at least 8 characters",
                                     key="new_password")
        
        confirm_password = st.text_input("Confirm New Password", 
                                         type="password",
                                         key="confirm_password")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            if st.button("Reset Password", type="primary", use_container_width=True):
                if not token or not new_password or not confirm_password:
                    st.warning("Please fill in all fields")
                elif len(token) != 6:
                    st.warning("Code must be 6 digits")
                elif new_password != confirm_password:
                    st.error("Passwords don't match")
                elif len(new_password) < 8:
                    st.warning("Password must be at least 8 characters")
                else:
                    success, msg = verify_and_reset_password(email, token, new_password)
                    if success:
                        st.success(msg)
                        st.balloons()
                        st.session_state.reset_mode = False
                        if 'reset_email' in st.session_state:
                            del st.session_state.reset_email
                        st.rerun()
                    else:
                        st.error(msg)
        
        with col2:
            if st.button("Resend Code", use_container_width=True):
                success, msg = request_password_reset(email)
                if success:
                    st.success("New code sent!")
                else:
                    st.error(msg)
        
        with col3:
            if st.button("Cancel"):
                st.session_state.reset_mode = False
                if 'reset_email' in st.session_state:
                    del st.session_state.reset_email
                st.rerun()

def sign_out():
    supabase.auth.sign_out()
    st.session_state.user_email = None
    st.session_state.user_id = None 
    st.rerun()
