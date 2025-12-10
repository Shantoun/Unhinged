from supabase import create_client, Client
import streamlit as st
import variables as var
from datetime import datetime


# --- SUPABASE INIT -----------------------------------------------------------

supabase_url = st.secrets["SUPABASE_URL"]      # e.g. "SUPABASE_URL"
supabase_key = st.secrets["SUPABASE_KEY"]      # e.g. "SUPABASE_KEY"

supabase: Client = create_client(supabase_url, supabase_key)



# --- MATCHES INGEST ----------------------------------------------------------



def matches_ingest(json_data, user_id):
    supabase = create_client("SUPABASE_URL", "SUPABASE_KEY")

    matches = json_data.get(var.json_matches, [])
    rows = []

    for m in matches:
        # pull the match timestamp from nested structure
        match_event = m.get("match")
        if not match_event or len(match_event) == 0:
            continue

        ts_str = match_event[0].get("timestamp")
        if not ts_str:
            continue

        ts = int(datetime.fromisoformat(ts_str).timestamp())

        match_id = f"match_{user_id}_{ts}"

        rows.append({
            var.col_match_id: match_id,
            var.col_match_timestamp: ts,
            var.col_user_id: user_id
        })

    if rows:
        supabase.table(var.table_matches).upsert(rows).execute()

    return len(rows)


