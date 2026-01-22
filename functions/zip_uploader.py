import streamlit as st
import zipfile
import tempfile
import os
import json
import functions.supabase_ingest as ingest


def zip_uploader():
    uploaded = st.file_uploader("Upload ZIP file", type=["zip"], accept_multiple_files=False)
    if not uploaded:
        return None

    tmpdir = tempfile.mkdtemp()
    zip_path = os.path.join(tmpdir, "hinge.zip")

    with open(zip_path, "wb") as f:
        f.write(uploaded.getbuffer())

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(tmpdir)

    data = {}
    for root, dirs, files in os.walk(tmpdir):
        for file in files:
            if file.endswith(".json"):
                full = os.path.join(root, file)
                key = os.path.basename(file).replace(".json", "")
                with open(full, "r") as f:
                    data[key] = json.load(f)

    return {"tmpdir": tmpdir, "json": data}



def uploader():
    result = zip_uploader()

    if result:
        st.caption("By clicking Continue, you acknowledge and agree that your data will be securely stored and analyzed, including in aggregated and anonymized form.")
        if st.button("Continue", type="primary", width="stretch"):
            json_data = result["json"]

            with st.spinner("Syncing matches..."):
                ingest.matches_ingest(json_data, st.session_state.user_id)
            
            with st.spinner("Syncing likes..."):
                ingest.likes_ingest(json_data, st.session_state.user_id)    
    
            with st.spinner("Syncing messages..."):
                ingest.messages_ingest(json_data, st.session_state.user_id)        
            
            with st.spinner("Syncing blocks..."):
                ingest.blocks_ingest(json_data, st.session_state.user_id)
    
            with st.spinner("Syncing user profile..."):
                ingest.user_profile_ingest(json_data, st.session_state.user_id)
                ingest.media_ingest(json_data, st.session_state.user_id)
                ingest.prompts_ingest(json_data, st.session_state.user_id)
                ingest.subscriptions_ingest(json_data, st.session_state.user_id)
    
            st.success("Done!")
            return True
