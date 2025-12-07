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




import streamlit as st
from supabase import create_client, Client
import streamlit.components.v1 as components

# Initialize Supabase client
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None
if 'auth_checked' not in st.session_state:
    st.session_state.auth_checked = False

def capture_url_fragment():
    """Capture URL fragment (tokens after #) using JavaScript"""
    fragment_script = """
    <script>
        // Get the URL fragment (everything after #)
        const fragment = window.location.hash.substring(1);
        
        if (fragment) {
            // Parse the fragment into key-value pairs
            const params = new URLSearchParams(fragment);
            const accessToken = params.get('access_token');
            const refreshToken = params.get('refresh_token');
            
            if (accessToken) {
                // Convert fragment to query params so Streamlit can read them
                const newUrl = window.location.pathname + '?access_token=' + accessToken + 
                              (refreshToken ? '&refresh_token=' + refreshToken : '');
                window.location.replace(newUrl);
            }
        }
    </script>
    """
    components.html(fragment_script, height=0)

def handle_oauth_callback():
    """Handle the OAuth callback from Supabase"""
    query_params = st.query_params
    
    if 'access_token' in query_params and not st.session_state.auth_checked:
        access_token = query_params['access_token']
        refresh_token = query_params.get('refresh_token', '')
        
        try:
            # Set the session with the tokens
            supabase.auth.set_session(access_token, refresh_token)
            
            # Get user info
            user_response = supabase.auth.get_user(access_token)
            st.session_state.user = user_response.user
            st.session_state.auth_checked = True
            
            # Clear query params
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Authentication error: {str(e)}")
            st.session_state.auth_checked = True

def login_with_google():
    """Initiate Google OAuth login"""
    try:
        redirect_url = "https://unhinged.streamlit.app/"
        
        response = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": redirect_url
            }
        })
        
        # Open OAuth URL in same window
        st.markdown(f"""
            <meta http-equiv="refresh" content="0;url={response.url}">
            <p>Redirecting to Google...</p>
        """, unsafe_allow_html=True)
        st.stop()
    except Exception as e:
        st.error(f"Error initiating login: {str(e)}")

def logout():
    """Log out the user"""
    try:
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.auth_checked = False
        st.rerun()
    except Exception as e:
        st.error(f"Logout error: {str(e)}")

# Main app
def main():
    st.title("Google OAuth with Supabase")
    
    # First, capture any URL fragments (tokens from OAuth)
    if not st.session_state.get('user'):
        capture_url_fragment()
    
    # Then handle the callback
    handle_oauth_callback()
    
    # Check if user is logged in
    if st.session_state.user:
        st.success(f"✅ Welcome, {st.session_state.user.email}!")
        
        # Display user info
        with st.expander("User Details"):
            st.json({
                "email": st.session_state.user.email,
                "id": st.session_state.user.id,
                "created_at": str(st.session_state.user.created_at)
            })
        
        st.write("---")
        st.write("You are now logged in and can access protected features!")
        
        if st.button("🚪 Logout", type="secondary"):
            logout()
    else:
        st.write("Please log in to continue")
        st.write("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔐 Login with Google", type="primary", use_container_width=True):
                with st.spinner("Redirecting to Google..."):
                    login_with_google()

if __name__ == "__main__":
    main()







# from supabase import create_client, Client
# import streamlit as st

# supabase_url = st.secrets["SUPABASE_URL"]
# supabase_key = st.secrets["SUPABASE_KEY"]
# supabase: Client = create_client(supabase_url, supabase_key)

# def smart_auth(email, password):
#     """Try login first, if it fails try signup"""
#     try:
#         user = supabase.auth.sign_in_with_password({"email": email, "password": password})
#         return user, "success", "Welcome back!"
#     except:
#         try:
#             user = supabase.auth.sign_up({"email": email, "password": password})
#             if user and user.user:
#                 if user.user.email_confirmed_at is None:
#                     return None, "check_email", f"Check your email ({email}) to confirm your account, then log in again."
#                 return user, "success", "Account created!"
#         except Exception as e:
#             if "already registered" in str(e).lower():
#                 return None, "error", "Wrong password."
#             return None, "error", f"Error: {e}"
#     return None, "error", "Authentication failed."

# def auth_screen():
#     st.title("🔐 Login or Sign Up")
#     email = st.text_input("Email")
#     password = st.text_input("Password", type="password")

#     if st.button("Continue", type="primary"):
#         if email and password:
#             user, status, msg = smart_auth(email, password)
#             if status == "success":
#                 st.session_state.user_email = user.user.email
#                 st.success(msg)
#                 st.rerun()
#             elif status == "check_email":
#                 st.info(msg)
#             else:
#                 st.error(msg)
#         else:
#             st.warning("Enter email and password")

# def main_app(user_email):
#     st.title("🎉 Welcome")
#     st.success(f"Welcome, {user_email}!")
#     if st.button("Logout"):
#         supabase.auth.sign_out()
#         st.session_state.user_email = None
#         st.rerun()

# if "user_email" not in st.session_state:
#     st.session_state.user_email = None

# if st.session_state.user_email:
#     main_app(st.session_state.user_email)
# else:
#     auth_screen()
