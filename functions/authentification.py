from supabase import create_client, Client
import streamlit as st


supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)



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
    st.header("Login or Sign Up")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    # --- Continue button ---
    if st.button("Continue", type="primary", use_container_width=True):
        if email and password:
            user, status, msg = smart_auth(email, password)

            if status == "success":
                st.session_state.user_email = user.user.email
                st.session_state.user_id = user.user.id
                st.success(msg)
                st.rerun()

            elif status == "check_email":
                st.info(msg)
            else:
                st.error(msg)
        else:
            st.warning("Enter email and password")


    # --- Forgot password (link style) ---
    st.markdown(
        "<p style='text-align:center;margin-top:0.5rem;'>"
        "<a href='javascript:void(0)' id='forgot-link' style='color:#4B9CFF;text-decoration:underline;'>"
        "Forgot password?"
        "</a></p>",
        unsafe_allow_html=True
    )

    # JS to capture click and notify Streamlit
    st.write("""
        <script>
        const link = window.parent.document.getElementById('forgot-link');
        if (link) {
            link.onclick = () => {
                window.parent.postMessage({ forgot_pw: true }, "*");
            };
        }
        </script>
    """, unsafe_allow_html=True)

    # Streamlit receives message
    msg = st.experimental_get_query_params().get("forgot_pw")

    if msg is not None:
        if email:
            auth.supabase.auth.reset_password_for_email(
                email,
                options={"redirect_to": "https://yourappurl.com/reset"}
            )
            st.success(f"Password reset link sent to {email}")
        else:
            st.warning("Enter your email to reset your password")






# def auth_screen():
#     st.header("Login or Sign Up")
#     email = st.text_input("Email")
#     password = st.text_input("Password", type="password", help="Must be at least 8 characters")

#     if st.button("Continue", type="primary"):
#         if email and password:
#             user, status, msg = smart_auth(email, password)
#             if status == "success":
#                 st.session_state.user_email = user.user.email
#                 st.session_state.user_id = user.user.id      # <-- THIS LINE
#                 st.success(msg)
#                 st.rerun()
#             elif status == "check_email":
#                 st.info(msg)
#             else:
#                 st.error(msg)
#         else:
#             st.warning("Enter email and password")



def sign_out():
        supabase.auth.sign_out()
        st.session_state.user_email = None
        st.session_state.user_id = None 
        st.rerun()



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

