from supabase import create_client, Client
import streamlit as st
import variables as var
from datetime import datetime
from functions.authentification import supabase




# --- MATCHES INGEST ---------------------------------------------------------
def matches_ingest(json_data, user_id):

    matches = json_data.get(var.json_matches, [])
    rows = []

    for m in matches:

        match_event = m.get(var.json_match_event)
        if not match_event:
            continue

        ts_str = match_event[0].get(var.json_timestamp)
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




# --- MATCHES INGEST ---------------------------------------------------------
from functions.authentification import supabase
import variables as var
from datetime import datetime


def blocks_ingest(json_data, user_id):

    blocks = json_data.get(var.json_blocks, [])
    rows = []

    for b in blocks:

        block_event = b.get(var.json_block_event)
        if not block_event:
            continue

        ts_str = block_event[0].get(var.json_timestamp)
        if not ts_str:
            continue

        ts = int(datetime.fromisoformat(ts_str).timestamp())

        match_id = b.get(var.col_match_id)
        block_type = block_event[0].get(var.json_block_type)

        block_id = f"block_{user_id}_{ts}"

        rows.append({
            var.col_block_id: block_id,
            var.col_block_timestamp: ts,
            var.col_user_id: user_id,
            var.col_match_id: match_id,
            var.col_block_type: block_type
        })

    if rows:
        supabase.table(var.table_blocks).upsert(rows).execute()




