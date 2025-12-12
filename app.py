
import streamlit as st
import functions.authentification as auth
from functions.zip_uploader import uploader
import variables as var

# Check if this is a password reset callback first
# Supabase adds fragment params like #access_token=...&type=recovery
# We need to handle the fragment with JavaScript since Streamlit can't access it directly
if "password_reset_mode" not in st.session_state:
    st.session_state.password_reset_mode = False

# Inject JavaScript to check for recovery token in URL fragment
st.markdown("""
<script>
    // Check if URL has recovery token in fragment
    const hash = window.location.hash;
    if (hash.includes('type=recovery') || hash.includes('type=magiclink')) {
        // Extract access_token and refresh_token from fragment
        const params = new URLSearchParams(hash.substring(1));
        const accessToken = params.get('access_token');
        const refreshToken = params.get('refresh_token');
        
        if (accessToken) {
            // Send tokens to Streamlit
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                key: 'recovery_tokens',
                value: {
                    access_token: accessToken,
                    refresh_token: refreshToken
                }
            }, '*');
        }
    }
</script>
""", unsafe_allow_html=True)

# Check for recovery tokens from JavaScript
recovery_data = st.query_params.get("access_token")
if recovery_data or st.session_state.password_reset_mode:
    st.session_state.password_reset_mode = True
    auth.password_reset_screen()
    st.stop()

# initialize the key so it always exists
if var.col_user_id not in st.session_state:
    st.session_state.user_id = None

user_id = st.session_state.user_id

# if logged in → main app
if user_id:
    
    res = auth.supabase.table(var.table_user_profile) \
        .select("*") \
        .eq(var.col_user_id, user_id) \
        .execute()
    
    has_profile = len(res.data) > 0
    
    @st.dialog("Sync Your Hinge Data")
    def hinge_sync_dialog():
        done = uploader()
        if done:
            st.rerun()
    
    if not has_profile:
        hinge_sync_dialog()
    else:
        if st.sidebar.button("Upload Data", use_container_width=True):
            hinge_sync_dialog()
    
    # Sign out
    if st.sidebar.button("Sign Out", use_container_width=True):
        auth.sign_out()
        st.rerun()

# if not logged in → show login screen
else:
    auth.auth_screen()
