import streamlit as st
from supabase import create_client

st.set_page_config(layout="centered")

# --- CONNECT TO SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
sb = create_client(url, key)

st.title("Unhinged Login")

# --- GOOGLE OAUTH URL ---
# (We generate it once. If Supabase accepts the Site URL, this will ALWAYS work.)
google = sb.auth.sign_in_with_oauth(
    {
        "provider": "google",
        "options": {"redirect_to": "https://unhinged.streamlit.app"},
    }
)

google_url = google.url


# --- EMAIL LOGIN / SIGNUP ---
email = st.text_input("Email")
password = st.text_input("Password", type="password")

col1, col2 = st.columns(2)

with col1:
    if st.button("Sign Up"):
        sb.auth.sign_up({"email": email, "password": password})
        st.success("Check your email to confirm your account.")

with col2:
    if st.button("Sign In"):
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            st.success(f"Logged in as: {res.user.email}")
        else:
            st.error("Invalid email or password.")


# --- GOOGLE LOGIN ---
st.write("---")
st.subheader("Or Sign In With Google")

if google_url:
    st.link_button("Continue with Google", google_url)
else:
    st.error("Google login is temporarily unavailable.")
