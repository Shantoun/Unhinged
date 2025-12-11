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

    # safety: if someone ever passes the top-level dict
    if isinstance(json_data, dict):
        json_data = json_data.get(var.json_matches, [])

    for m in json_data:
        if not isinstance(m, dict):
            continue

        # ---------- build match_id if there is a match ----------
        match_id = None
        match_event = m.get(var.json_match_event)
        if isinstance(match_event, list) and match_event:
            ts_match_str = match_event[0].get(var.json_timestamp)
            if ts_match_str:
                match_ts = int(datetime.fromisoformat(ts_match_str).timestamp())
                match_id = f"match_{user_id}_{match_ts}"

        # ---------- likes (works for matched + standalone likes) ----------
        outer_likes = m.get(var.json_like_key, [])
        if not isinstance(outer_likes, list):
            continue

        for outer in outer_likes:
            if not isinstance(outer, dict):
                continue

            inner_likes = outer.get(var.json_like_key)

            # case 1: real likes in inner list (your JSON)
            if isinstance(inner_likes, list) and inner_likes:
                for inner in inner_likes:
                    if not isinstance(inner, dict):
                        continue

                    ts_str = inner.get(var.json_timestamp)
                    if not ts_str:
                        continue

                    ts_int = int(datetime.fromisoformat(ts_str).timestamp())
                    like_id = f"like_{user_id}_{ts_int}"

                    rows.append({
                        var.col_like_id:         like_id,
                        var.col_like_timestamp:  ts_int,
                        var.col_user_id:         user_id,
                        var.col_match_id:        match_id,   # None for pure-like rows
                    })

            # case 2: fallback if outer itself is the like event
            else:
                ts_str = outer.get(var.json_timestamp)
                if not ts_str:
                    continue

                ts_int = int(datetime.fromisoformat(ts_str).timestamp())
                like_id = f"like_{user_id}_{ts_int}"

                rows.append({
                    var.col_like_id:         like_id,
                    var.col_like_timestamp:  ts_int,
                    var.col_user_id:         user_id,
                    var.col_match_id:        match_id,
                })

    if rows:
        supabase.table(var.table_likes).upsert(rows).execute()






# --- MESSAGES INGEST ---------------------------------------------------------
def messages_ingest(json_data, user_id):

    rows = []

    # allow dict if someone passed uploader output incorrectly
    if isinstance(json_data, dict):
        json_data = json_data.get(var.json_matches, [])

    for m in json_data:
        if not isinstance(m, dict):
            continue

        # ------------------------------
        # BUILD match_id (if exists)
        # ------------------------------
        match_id = None
        match_event = m.get(var.json_match_event)
        if isinstance(match_event, list) and match_event:
            ts_str = match_event[0].get(var.json_timestamp)
            if ts_str:
                ts_int = int(datetime.fromisoformat(ts_str).timestamp())
                match_id = f"match_{user_id}_{ts_int}"

        # =====================================================
        # 1) CHAT MESSAGES (stored under "chats")
        # =====================================================
        chats = m.get(var.json_chats, [])
        for chat in chats:
            if not isinstance(chat, dict):
                continue

            body = chat.get(var.json_body)
            ts_str = chat.get(var.json_timestamp)

            if not body or not ts_str:
                continue

            ts_int = int(datetime.fromisoformat(ts_str).timestamp())
            message_id = f"message_{user_id}_{ts_int}"

            rows.append({
                var.col_message_id:        message_id,
                var.col_message_timestamp: ts_int,
                var.col_user_id:           user_id,
                var.col_message_body:      body,
                var.col_match_id:          match_id,
                var.col_like_id:           None
            })

        # =====================================================
        # 2) LIKE COMMENTS (nested under "like")
        # =====================================================
        outer_likes = m.get(var.json_like_key, [])
        for outer in outer_likes:

            inner_likes = outer.get(var.json_like_key, [])
            for inner in inner_likes:
                comment = inner.get(var.json_comment)
                ts_str  = inner.get(var.json_timestamp)

                if not ts_str or not comment:
                    continue

                ts_int = int(datetime.fromisoformat(ts_str).timestamp())
                message_id = f"message_{user_id}_{ts_int}"

                # like_id must match likes_ingest logic
                like_id = f"like_{user_id}_{ts_int}"

                rows.append({
                    var.col_message_id:        message_id,
                    var.col_message_timestamp: ts_int,
                    var.col_user_id:           user_id,
                    var.col_message_body:      comment,
                    var.col_match_id:          match_id,   # often exists, sometimes None
                    var.col_like_id:           like_id     # link comment → like
                })

    if rows:
        supabase.table(var.table_messages).upsert(rows).execute()



