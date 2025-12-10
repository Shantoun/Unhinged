from supabase import create_client, Client
import streamlit as st
import variables as var


# --- SUPABASE INIT -----------------------------------------------------------

supabase_url = st.secrets[var.supabase_url]      # e.g. "SUPABASE_URL"
supabase_key = st.secrets[var.supabase_key]      # e.g. "SUPABASE_KEY"

supabase: Client = create_client(supabase_url, supabase_key)



# --- MATCHES INGEST ----------------------------------------------------------

def matches_ingest(json_data, user_id):
    """
    json_data: uploader()["json"]
    user_id:   Supabase authenticated user's ID
    """

    matches = json_data.get(var.matches)
    if not matches:
        return

    rows = []

    for m in matches:
        match_id = m.get(var.match_id)
        ts       = m.get(var.timestamp)

        if not match_id or not ts:
            continue

        rows.append({
            var.match_id: match_id,
            var.match_timestamp: ts,
            var.user_id: user_id
        })

    if rows:
        supabase.table(var.matches_table).upsert(rows).execute()
