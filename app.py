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
        return user, "Welcome back!"
    except Exception as sign_in_error:
        # If sign in fails, try to sign up
        try:
            user = supabase.auth.sign_up({"email": email, "password": password})
            if user and user.user:
                return user, "Account created! You're now logged in."
            return None, "Registration failed"
        except Exception as sign_up_error:
            # Check if it's a wrong password error
            if "Invalid login credentials" in str(sign_in_error):
                return None, "Incorrect password. Please try again."
            return None, f"Authentication failed: {sign_up_error}"

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
                user, message = smart_auth(email, password)
                if user and user.user:
                    st.session_state.user_email = user.user.email
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        else:
            st.warning("Please enter both email and password")

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if st.session_state.user_email:
    main_app(st.session_state.user_email)
else:
    auth_screen()









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
