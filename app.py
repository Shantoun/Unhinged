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








from supabase import create_client, Client
import streamlit as st

supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(supabase_url, supabase_key)

def smart_auth(email, password):
    """Try to sign in, if fails then sign up automatically"""
    try:
        # First try to sign in
        user = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return user, "logged_in", "Welcome back!"
    except Exception as sign_in_error:
        error_msg = str(sign_in_error)
        
        # Check if email not confirmed
        if "Email not confirmed" in error_msg or "not confirmed" in error_msg:
            return None, "unconfirmed", "Please check your email and click the confirmation link before logging in."
        
        # For "Invalid login credentials", try to sign up (could be new user or wrong password)
        if "Invalid login credentials" in error_msg or "Invalid" in error_msg:
            try:
                # Sign up with redirect URL
                redirect_url = st.secrets.get("SITE_URL", "http://localhost:8501")
                user = supabase.auth.sign_up({
                    "email": email, 
                    "password": password,
                    "options": {
                        "email_redirect_to": redirect_url
                    }
                })
                if user and user.user:
                    # Check if email confirmation is required
                    if user.user.email_confirmed_at is None:
                        return user, "confirmation_sent", f"Account created! Check your email ({email}) for a confirmation link."
                    else:
                        # Email confirmation disabled in Supabase
                        return user, "logged_in", "Account created! You're now logged in."
                return None, "error", "Registration failed"
            except Exception as sign_up_error:
                signup_error_msg = str(sign_up_error)
                # If signup fails because user already exists, it means wrong password
                if "already registered" in signup_error_msg or "already exists" in signup_error_msg:
                    return None, "error", "Incorrect password. Please try again."
                return None, "error", f"Authentication failed: {sign_up_error}"
        
        # Other errors
        return None, "error", f"Authentication failed: {sign_in_error}"

def sign_out():
    try:
        supabase.auth.sign_out()
        st.session_state.user_email = None
        st.rerun()
    except Exception as e:
        st.error(f"Logout failed: {e}")

def main_app(user_email):
    st.title("🎉 Welcome Page")
    st.success(f"Welcome, {user_email}! 👋")
    if st.button("Logout"):
        sign_out()

def auth_screen():
    st.title("🔐 Login or Sign Up")
    st.write("Enter your credentials - we'll figure out the rest!")
    
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Continue", type="primary"):
        if email and password:
            with st.spinner("Authenticating..."):
                user, status, message = smart_auth(email, password)
                
                if status == "logged_in" and user and user.user:
                    st.session_state.user_email = user.user.email
                    st.success(message)
                    st.rerun()
                elif status == "confirmation_sent":
                    st.info(message)
                    st.info("📧 After confirming your email, come back and click 'Continue' again to log in.")
                elif status == "unconfirmed":
                    st.warning(message)
                else:
                    st.error(message)
        else:
            st.warning("Please enter both email and password")

if "user_email" not in st.session_state:
    st.session_state.user_email = None

# Handle email confirmation callback
query_params = st.query_params
if "token_hash" in query_params and "type" in query_params:
    try:
        token_hash = query_params["token_hash"]
        token_type = query_params["type"]
        
        # Verify the OTP token
        response = supabase.auth.verify_otp({
            "token_hash": token_hash,
            "type": token_type
        })
        
        if response and response.user:
            st.session_state.user_email = response.user.email
            st.query_params.clear()
            st.success("Email confirmed! You're now logged in. 🎉")
            st.rerun()
    except Exception as e:
        st.error(f"Confirmation failed: {e}")
        st.query_params.clear()

if st.session_state.user_email:
    main_app(st.session_state.user_email)
else:
    auth_screen()










# from supabase import create_client, Client
# import streamlit as st

# supabase_url = st.secrets["SUPABASE_URL"]
# supabase_key = st.secrets["SUPABASE_KEY"]

# supabase: Client = create_client(supabase_url, supabase_key)

# def smart_auth(email, password):
#     """Try to sign in, if fails then sign up automatically"""
#     try:
#         # First try to sign in
#         user = supabase.auth.sign_in_with_password({"email": email, "password": password})
#         return user, "logged_in", "Welcome back!"
#     except Exception as sign_in_error:
#         error_msg = str(sign_in_error)
        
#         # Check if email not confirmed
#         if "Email not confirmed" in error_msg or "not confirmed" in error_msg:
#             return None, "unconfirmed", "Please check your email and click the confirmation link before logging in."
        
#         # For "Invalid login credentials", try to sign up (could be new user or wrong password)
#         if "Invalid login credentials" in error_msg or "Invalid" in error_msg:
#             try:
#                 user = supabase.auth.sign_up({"email": email, "password": password})
#                 if user and user.user:
#                     # Check if email confirmation is required
#                     if user.user.email_confirmed_at is None:
#                         return user, "confirmation_sent", f"Account created! Check your email ({email}) for a confirmation link."
#                     else:
#                         # Email confirmation disabled in Supabase
#                         return user, "logged_in", "Account created! You're now logged in."
#                 return None, "error", "Registration failed"
#             except Exception as sign_up_error:
#                 signup_error_msg = str(sign_up_error)
#                 # If signup fails because user already exists, it means wrong password
#                 if "already registered" in signup_error_msg or "already exists" in signup_error_msg:
#                     return None, "error", "Incorrect password. Please try again."
#                 return None, "error", f"Authentication failed: {sign_up_error}"
        
#         # Other errors
#         return None, "error", f"Authentication failed: {sign_in_error}"

# def sign_out():
#     try:
#         supabase.auth.sign_out()
#         st.session_state.user_email = None
#         st.rerun()
#     except Exception as e:
#         st.error(f"Logout failed: {e}")

# def main_app(user_email):
#     st.title("🎉 Welcome Page")
#     st.success(f"Welcome, {user_email}! 👋")
#     if st.button("Logout"):
#         sign_out()

# def auth_screen():
#     st.title("🔐 Login or Sign Up")
#     st.write("Enter your credentials - we'll figure out the rest!")
    
#     email = st.text_input("Email")
#     password = st.text_input("Password", type="password")

#     if st.button("Continue", type="primary"):
#         if email and password:
#             with st.spinner("Authenticating..."):
#                 user, status, message = smart_auth(email, password)
                
#                 if status == "logged_in" and user and user.user:
#                     st.session_state.user_email = user.user.email
#                     st.success(message)
#                     st.rerun()
#                 elif status == "confirmation_sent":
#                     st.info(message)
#                     st.info("📧 After confirming your email, come back and click 'Continue' again to log in.")
#                 elif status == "unconfirmed":
#                     st.warning(message)
#                 else:
#                     st.error(message)
#         else:
#             st.warning("Please enter both email and password")

# if "user_email" not in st.session_state:
#     st.session_state.user_email = None

# # Check for email confirmation tokens in URL
# if not st.session_state.user_email:
#     try:
#         # Get query parameters from URL
#         query_params = st.query_params
        
#         # Check if there's an access token (from email confirmation)
#         if "access_token" in query_params or "token_hash" in query_params:
#             # Exchange the token for a session
#             user = supabase.auth.get_user()
#             if user and user.user:
#                 st.session_state.user_email = user.user.email
#                 # Clear URL parameters
#                 st.query_params.clear()
#                 st.success("Email confirmed! You're now logged in. 🎉")
#                 st.rerun()
#     except Exception as e:
#         # If token exchange fails, just continue to login screen
#         pass

# if st.session_state.user_email:
#     main_app(st.session_state.user_email)
# else:
#     auth_screen()

