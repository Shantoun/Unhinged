import streamlit as st
from supabase import create_client

st.set_page_config(layout="wide")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
sb = create_client(url, key)

st.title("Unhinged Login")

# --- EMAIL LOGIN ---
st.subheader("Email Login")

email = st.text_input("Email")
password = st.text_input("Password", type="password")

c1, c2 = st.columns(2)

with c1:
    if st.button("Sign Up"):
        sb.auth.sign_up({"email": email, "password": password})
        st.success("Check your email to confirm your account.")

with c2:
    if st.button("Sign In"):
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            st.success(f"Logged in as: {res.user.email}")
        else:
            st.error("Invalid email or password")

# --- GOOGLE LOGIN ---
# Create the redirect URL ONCE, not inside button click
google = sb.auth.sign_in_with_oauth(
    {
        "provider": "google",
        "options": {
            "redirect_to": "http://localhost:8501"   # must match Supabase dashboard
        }
    }
)

if google and google.url:
    st.link_button("Sign In with Google", google.url)
