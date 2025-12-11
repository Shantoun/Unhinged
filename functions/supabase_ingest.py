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

    rows = []

    # make sure json_data is a parsed object
    if isinstance(json_data, str):
        json_data = json.loads(json_data)

    # match shape used by matches_ingest
    if isinstance(json_data, dict):
        items = json_data.get(var.json_matches, [])
    else:
        items = json_data or []

    for m in items:
        if not isinstance(m, dict):
            continue

        # try to reconstruct match_id (may be None for orphan blocks)
        match_id = None
        match_event = m.get(var.json_match_event)
        if match_event:
            ts_str_match = match_event[0].get(var.json_timestamp)
            if ts_str_match:
                match_ts = int(datetime.fromisoformat(ts_str_match).timestamp())
                match_id = f"match_{user_id}_{match_ts}"

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
                var.col_match_id:        match_id,      # can be None for orphan blocks
                var.col_block_type:      block_type,
            })

    if rows:
        supabase.table(var.table_blocks).upsert(rows).execute()






# --- LIKES INGEST ---------------------------------------------------------
def likes_ingest(json_data, user_id):
    rows = []

    for m in json_data:
        if not isinstance(m, dict):
            continue

        # build match_id if available
        match_id = None
        match_event = m.get(var.json_match_event)
        if match_event:
            ts_str = match_event[0].get(var.json_timestamp)
            if ts_str:
                match_ts = int(datetime.fromisoformat(ts_str).timestamp())
                match_id = f"match_{user_id}_{match_ts}"

        # real like events are inside: m["like"][0]["like"]
        outer_like_events = m.get(var.json_likes, [])
        for outer in outer_like_events:

            inner_like_events = outer.get(var.json_likes, [])
            for inner in inner_like_events:

                ts_str = inner.get(var.json_timestamp)
                if not ts_str:
                    continue

                ts = int(datetime.fromisoformat(ts_str).timestamp())
                like_id = f"like_{user_id}_{ts}"

                rows.append({
                    var.col_like_id:        like_id,
                    var.col_like_timestamp: ts,
                    var.col_user_id:        user_id,
                    var.col_match_id:       match_id
                })

    if rows:
        supabase.table(var.table_likes).upsert(rows).execute()


