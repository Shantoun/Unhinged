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

# Handle OAuth callback
params = st.query_params
if "code" in params:
    code = params["code"]
    try:
        session = supabase.auth.exchange_code_for_session({"code": code})
        st.session_state.user_email = session.user.email
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"OAuth failed: {e}")
        st.query_params.clear()

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

def auth_screen():
    st.title("🔐 Login or Sign Up")
    
    # Google Sign In
    if st.button("🔵 Continue with Google", use_container_width=True):
        res = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": "https://unhinged.streamlit.app/",
                "flow_type": "pkce"
            }
        })
        auth_url = res.url
        st.markdown(f'<meta http-equiv="refresh" content="0;url={auth_url}">', unsafe_allow_html=True)
        st.stop()
    
    st.divider()
    st.write("Or use email and password:")
    
    # Email/Password
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Continue", type="primary"):
        if email and password:
            user, status, msg = smart_auth(email, password)
            if status == "success":
                st.session_state.user_email = user.user.email
                st.success(msg)
                st.rerun()
            elif status == "check_email":
                st.info(msg)
            else:
                st.error(msg)
        else:
            st.warning("Enter email and password")

def main_app(user_email):
    st.title("🎉 Welcome")
    st.success(f"Welcome, {user_email}!")
    if st.button("Logout"):
        supabase.auth.sign_out()
        st.session_state.user_email = None
        st.rerun()

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if st.session_state.user_email:
    main_app(st.session_state.user_email)
else:
    auth_screen()





