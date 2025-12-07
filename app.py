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
import uuid

supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)

def ensure_supabase_user(email):
    # Generate a random internal password for Supabase
    internal_password = str(uuid.uuid4())

    # Try login first
    try:
        user = supabase.auth.sign_in_with_password({
            "email": email,
            "password": internal_password
        })
        return user
    except:
        # Create them silently if not found
        user = supabase.auth.sign_up({
            "email": email,
            "password": internal_password
        })
        return user


# ---- STREAMLIT AUTH ----

if not st.user.is_logged_in:
    st.title("Sign in")
    
    if st.button("Sign in with Google"):
        st.login("google")

else:
    st.title("Logged in through Google")
    st.write(f"Google Email: {st.user.email}")

    # Sync to Supabase
    supa_user = ensure_supabase_user(st.user.email)

    st.success(f"Supabase synced as: {supa_user.user.email}")

    if st.button("Sign out"):
        st.logout()








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






