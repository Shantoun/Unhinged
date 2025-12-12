import streamlit as st
import functions.authentification as auth
from functions.zip_uploader import uploader
import variables as var

# CRITICAL: Check URL for reset tokens on every load
# This JavaScript extracts tokens from URL hash and converts to query params
reset_detector = """
<script>
    // Run immediately on page load
    (function() {
        const hash = window.location.hash;
        const search = window.location.search;
        
        // Check if we already have query params (already processed)
        const urlParams = new URLSearchParams(search);
        if (urlParams.get('type') === 'recovery') {
            console.log('Already in recovery mode via query params');
            return;
        }
        
        // Check hash for recovery tokens
        if (hash && hash.includes('type=recovery')) {
            console.log('Found recovery tokens in hash:', hash);
            const hashParams = new URLSearchParams(hash.substring(1));
            const accessToken = hashParams.get('access_token');
            const refreshToken = hashParams.get('refresh_token');
            const type = hashParams.get('type');
            
            if (type === 'recovery' && accessToken && refreshToken) {
                console.log('Redirecting to query params...');
                const url = new URL(window.location.href);
                url.search = '?type=recovery&access_token=' + encodeURIComponent(accessToken) + '&refresh_token=' + encodeURIComponent(refreshToken);
                url.hash = '';
                window.location.replace(url.toString());
            }
        }
    })();
</script>
"""

st.markdown(reset_detector, unsafe_allow_html=True)

# Now check if we have recovery params
if st.query_params.get("type") == "recovery":
    access_token = st.query_params.get("access_token")
    refresh_token = st.query_params.get("refresh_token")
    
    if access_token and refresh_token:
        st.session_state.reset_access_token = access_token
        st.session_state.reset_refresh_token = refresh_token
        st.session_state.password_reset_mode = True

# If we're in password reset mode, show that screen and stop
if st.session_state.get("password_reset_mode", False):
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
