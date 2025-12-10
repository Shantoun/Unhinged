from supabase import create_client, Client
import streamlit as st
import variables as var


# --- SUPABASE INIT -----------------------------------------------------------

supabase_url = st.secrets[var.supabase_url]      # e.g. "SUPABASE_URL"
supabase_key = st.secrets[var.supabase_key]      # e.g. "SUPABASE_KEY"

supabase: Client = create_client(supabase_url, supabase_key)



# --- MATCHES INGEST ----------------------------------------------------------

def matches_ingest(json_data, user_id):
    matches = json_data.get(var.json_matches)
    if not matches:
        return

    rows = []

    for m in matches:
        ts = m.get(var.json_timestamp)
        if not ts:
            continue

        # create match_id using your rule
        match_id = f"match_{user_id}_{ts}"

        rows.append({
            var.col_match_id: match_id,
            var.col_match_timestamp: ts,
            var.col_user_id: user_id
        })

    if rows:
        supabase.table(var.table_matches).upsert(rows).execute()




