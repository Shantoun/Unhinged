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

# Initialize Supabase
@st.cache_resource
def init_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

supabase = init_supabase()

# Initialize session state
if "user" not in st.session_state:
    st.session_state.user = None

# Check for existing session on load
if st.session_state.user is None:
    try:
        session = supabase.auth.get_session()
        if session:
            st.session_state.user = session.user
    except:
        pass

def sign_up(email, password):
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        if response.user:
            st.success("Check your email to confirm!")
        return response
    except Exception as e:
        st.error(f"Sign up failed: {e}")
        return None

def sign_in(email, password):
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            st.session_state.user = response.user
            st.rerun()
        return response
    except Exception as e:
        st.error(f"Login failed: {e}")
        return None

def sign_in_with_google():
    try:
        response = supabase.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": st.secrets.get("REDIRECT_URL", "http://localhost:8501")
            }
        })
        if response.url:
            st.markdown(f'<meta http-equiv="refresh" content="0;url={response.url}">', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Google sign in failed: {e}")

def sign_out():
    try:
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()
    except Exception as e:
        st.error(f"Logout failed: {e}")

# Main UI
if st.session_state.user:
    st.title("🎉 Welcome!")
    st.success(f"Logged in as: {st.session_state.user.email}")
    
    if st.button("Logout"):
        sign_out()
else:
    st.title("🔐 Login")
    
    # Google Sign In Button
    if st.button("🔵 Sign in with Google", use_container_width=True):
        sign_in_with_google()
    
    st.divider()
    st.write("Or use email/password:")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", key="login_btn"):
            if email and password:
                sign_in(email, password)
            else:
                st.error("Please enter email and password")
    
    with tab2:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        
        if st.button("Sign Up", key="signup_btn"):
            if email and password:
                sign_up(email, password)
            else:
                st.error("Please enter email and password")












# from supabase import create_client, Client


# supabase_url = st.secrets["SUPABASE_URL"]
# supabase_key = st.secrets["SUPABASE_KEY"]

# supabase: Client = create_client(supabase_url, supabase_key)

# def sign_up(email, password):
#     try:
#         user = supabase.auth.sign_up({"email": email, "password": password})
#         return user
#     except Exception as e:
#         st.error(f"Registration failed: {e}")

# def sign_in(email, password):
#     try:
#         user = supabase.auth.sign_in_with_password({"email": email, "password": password})
#         return user
#     except Exception as e:
#         st.error(f"Login failed: {e}")

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
#     st.title("🔐 Streamlit & Supabase Auth App")
#     option = st.selectbox("Choose an action:", ["Login", "Sign Up"])
#     email = st.text_input("Email")
#     password = st.text_input("Password", type="password")

#     if option == "Sign Up" and st.button("Register"):
#         user = sign_up(email, password)
#         if user and user.user:
#             st.success("Registration successful. Please log in.")

#     if option == "Login" and st.button("Login"):
#         user = sign_in(email, password)
#         if user and user.user:
#             st.session_state.user_email = user.user.email
#             st.success(f"Welcome back, {email}!")
#             st.rerun()

# if "user_email" not in st.session_state:
#     st.session_state.user_email = None

# if st.session_state.user_email:
#     main_app(st.session_state.user_email)
# else:
#     auth_screen()
