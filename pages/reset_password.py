import streamlit as st
from supabase import create_client, Client
from authentification import supabase


st.set_page_config(page_title="Reset Password", page_icon="🔑")

st.header("🔑 Reset Your Password")

# Get the access token from URL parameters
access_token = st.query_params.get("access_token")

if not access_token:
    st.error("Invalid or expired reset link. Please request a new password reset.")
    if st.button("Back to Login"):
        st.switch_page("app.py")  # Replace with your main app file name
    st.stop()

st.write("Enter your new password below:")

new_password = st.text_input("New Password", type="password", help="Must be at least 8 characters")
confirm_password = st.text_input("Confirm Password", type="password")

if st.button("Reset Password", type="primary"):
    if not new_password or not confirm_password:
        st.warning("Please fill in both fields")
    elif len(new_password) < 8:
        st.warning("Password must be at least 8 characters")
    elif new_password != confirm_password:
        st.error("Passwords don't match")
    else:
        try:
            # Set the session with the access token
            supabase.auth.set_session(access_token, st.query_params.get("refresh_token", ""))
            
            # Update the password
            supabase.auth.update_user({"password": new_password})
            
            st.success("✅ Password reset successful! Redirecting to login...")
            st.balloons()
            
            # Clear the tokens from URL and redirect
            st.query_params.clear()
            
            import time
            time.sleep(2)
            st.switch_page("app.py")  # Replace with your main app file name
            
        except Exception as e:
            st.error(f"Error resetting password: {e}")
            st.info("Your reset link may have expired. Please request a new one.")

st.divider()
if st.button("← Back to Login"):
    st.switch_page("app.py")
