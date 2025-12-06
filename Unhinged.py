# import streamlit as st
# from supabase_client import get_client

# st.title("Unhinged")
# st.write("Analyze your game.")
 
import streamlit as st
from supabase import create_client

st.set_page_config(layout="wide")

# connect
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
sb = create_client(url, key)

st.title("Unhinged Login")

# --- EMAIL LOGIN ---
st.subheader("Email Login")

email = st.text_input("Email")
password = st.text_input("Password", type="password")

col1, col2 = st.columns(2)

with col1:
    if st.button("Sign Up", width='stretch'):
        sb.auth.sign_up({"email": email, "password": password})
        st.success("Check your email to confirm your account.")

with col2:
    if st.button("Sign In", width='stretch'):
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            st.success(f"Logged in as: {res.user.email}")
        else:
            st.error("Invalid email or password")


# --- GOOGLE LOGIN ---
if st.button("Or Sign In With Google", width='stretch'):
    redirect_url = sb.auth.sign_in_with_oauth({"provider": "google"})
    st.write("Click the link below to sign in:")
    st.write(redirect_url.url)
