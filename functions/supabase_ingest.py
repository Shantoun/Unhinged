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



# --- MEDIA INGEST ---------------------------------------------------------
def media_ingest(json_data, user_id):
    rows = []

    # json_data is the global export (matches + blocks + media + ...)
    # pull the media list safely
    media_list = json_data.get(var.json_media, [])
    if not isinstance(media_list, list):
        return

    for item in media_list:
        if not isinstance(item, dict):
            continue

        url = item.get(var.json_media_url)
        if not url:
            continue

        media_type = item.get(var.json_media_type)
        from_social = item.get(var.json_media_social, False)

        # extract basename: https://.../abc123.jpg -> abc123
        try:
            basename = url.split("/")[-1].split(".")[0]
        except:
            continue

        media_id = f"media_{user_id}_{basename}"

        rows.append({
            var.col_media_id:     media_id,
            var.col_media_url:    url,
            var.col_media_type:   media_type,
            var.col_media_social: from_social,
            var.col_user_id:      user_id
        })

    if rows:
        supabase.table(var.table_media).upsert(rows).execute()






# --- PROMPTS INGEST ---------------------------------------------------------
def prompts_ingest(json_data, user_id):
    rows = []

    # pull correct list depending on shape
    if isinstance(json_data, dict):
        prompts_list = json_data.get(var.json_prompts, [])
    else:
        prompts_list = json_data

    for p in prompts_list:
        prompt_raw_id = p.get(var.json_prompt_id)
        if prompt_raw_id is None:
            continue

        created = p.get(var.json_prompt_created)
        updated = p.get(var.json_prompt_updated)

        try:
            created_ts = int(datetime.fromisoformat(created).timestamp()) if created else None
        except:
            created_ts = None

        try:
            updated_ts = int(datetime.fromisoformat(updated).timestamp()) if updated else None
        except:
            updated_ts = created_ts

        prompt_type  = p.get(var.json_prompt_type)
        prompt_label = p.get(var.json_prompt_label)
        prompt_text  = p.get(var.json_prompt_text)

        # id format: prompt_userid_promptid_createdtimestamp
        base = created_ts if created_ts else 0
        prompt_id = f"prompt_{user_id}_{prompt_raw_id}_{base}"

        rows.append({
            var.col_prompt_id:         prompt_id,
            var.col_user_id:           user_id,
            var.col_prompt_type:       prompt_type,
            var.col_prompt_label:      prompt_label,
            var.col_prompt_text:       prompt_text,
            var.col_prompt_created_ts: created_ts,
            var.col_prompt_updated_ts: updated_ts
        })

    if rows:
        supabase.table(var.table_prompts).upsert(rows).execute()



# --- SUBSCRIPTIONS INGEST ---------------------------------------------------------
def subscriptions_ingest(json_data, user_id):
    rows = []

    subs = json_data.get(var.json_subscriptions, [])
    if not isinstance(subs, list):
        return

    for s in subs:
        sid        = s.get(var.json_sub_id)
        duration   = s.get(var.json_sub_duration)
        price      = s.get(var.json_sub_price)
        currency   = s.get(var.json_sub_currency)
        start_str  = s.get(var.json_sub_start_date)
        end_str    = s.get(var.json_sub_end_date)
        sub_type   = s.get(var.json_sub_type)

        if not sid or not start_str:
            continue

        start_ts = int(datetime.fromisoformat(start_str.replace("Z", "")).timestamp())
        end_ts   = int(datetime.fromisoformat(end_str.replace("Z", "")).timestamp()) if end_str else None

        sub_id = f"subscription_{user_id}_{sid}_{start_ts}"

        row = {
            var.col_subscription_id:       sub_id,
            var.col_subscription_start_ts: start_ts,
            var.col_subscription_end_ts:   end_ts,
            var.col_subscription_price:    price,
            var.col_subscription_currency: currency,
            var.col_subscription_type:     sub_type,
            var.col_user_id:               user_id
        }

        rows.append(row)

    if rows:
        supabase.table(var.table_subscriptions).upsert(rows).execute()



# --- USER PROFILE INGEST ---------------------------------------------------------
def user_profile_ingest(json_data, user_id):

    row = {
        var.col_user_id:     user_id,
        var.col_preferences: json_data.get(var.json_user_preferences),
        var.col_location:    json_data.get(var.json_user_location),
        var.col_identity:    json_data.get(var.json_user_identity),
        var.col_profile:     json_data.get(var.json_user_profile),
        var.col_account:     json_data.get(var.json_user_account)
    }

    existing = supabase.table(var.table_user_profile).select("*").eq(var.col_user_id, user_id).execute()

    if existing.data:
        prev = existing.data[0].get(var.col_upload_count, 0)
        row[var.col_upload_count] = prev + 1
    else:
        row[var.col_upload_count] = 1

    supabase.table(var.table_user_profile).upsert(row).execute()
