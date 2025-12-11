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




# --- BLOCKS INGEST ---------------------------------------------------------
def blocks_ingest(json_data, user_id):

    # json_data is the same top-level list used for matches
    matches = json_data.get(var.json_matches, [])
    rows = []

    for m in matches:
        # 1) get the match timestamp to build the SAME match_id as matches_ingest
        match_event = m.get(var.json_match_event)
        if not match_event:
            continue

        match_ts_str = match_event[0].get(var.json_timestamp)
        if not match_ts_str:
            continue

        match_ts = int(datetime.fromisoformat(match_ts_str).timestamp())
        match_id = f"match_{user_id}_{match_ts}"

        # 2) get block entries for this match
        block_events = m.get(var.json_block_event, [])
        if not block_events:
            continue

        for be in block_events:
            ts_str = be.get(var.json_timestamp)
            if not ts_str:
                continue

            ts = int(datetime.fromisoformat(ts_str).timestamp())
            block_type = be.get(var.json_block_type)

            block_id = f"block_{user_id}_{ts}"

            rows.append({
                var.col_block_id:        block_id,
                var.col_block_timestamp: ts,
                var.col_user_id:         user_id,
                var.col_match_id:        match_id,
                var.col_block_type:      block_type,
            })

    if rows:
        supabase.table(var.table_blocks).upsert(rows).execute()



