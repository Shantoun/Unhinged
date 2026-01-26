import variables as var
from functions.authentification import supabase
from functions.authentification import supabase_admin

import io
import zipfile
import hashlib
from datetime import datetime, timezone





# --------------------------------------------------
# Helpers
# --------------------------------------------------
def norm(ts: str) -> str:
    return ts.replace("-", "").replace(":", "").replace(".", "").replace(" ", "")


# --------------------------------------------------
# MATCHES
# --------------------------------------------------
def matches_ingest(json_data, user_id):

    rows = []

    for m in json_data.get(var.json_matches, []):
        match_event = m.get(var.json_match_event)
        if not match_event:
            continue

        match_ts = match_event[0].get(var.json_timestamp)
        if not match_ts:
            continue

        match_id = f"match_{user_id}_{norm(match_ts)}"

        # defaults so NOT NULL never gets NULL
        row = {
            var.col_match_id: match_id,
            var.col_match_timestamp: match_ts,
            var.col_user_id: user_id,
            var.col_we_met: False,
            var.col_my_type: False,
            var.col_we_met_timestamp : None,
        }

        we_met_events = m.get(var.col_we_met, [])
        if we_met_events:
            latest = max(
                (e for e in we_met_events if e.get(var.json_timestamp)),
                key=lambda e: e[var.json_timestamp],
                default=None
            )

            if latest and latest.get(var.json_we_met) == "Yes":
                row[var.col_we_met] = True
                row[var.col_we_met_timestamp] = latest.get(var.json_timestamp)

                if latest.get(var.json_my_type) is True:
                    row[var.col_my_type] = True

        rows.append(row)

    if rows:
        supabase.table(var.table_matches).upsert(rows).execute()




# --------------------------------------------------
# BLOCKS
# --------------------------------------------------
def blocks_ingest(json_data, user_id):

    rows = []

    for m in json_data.get(var.json_matches, []):
        match_id = None
        match_event = m.get(var.json_match_event)
        if match_event:
            ts_match = match_event[0].get(var.json_timestamp)
            if ts_match:
                match_id = f"match_{user_id}_{norm(ts_match)}"

        for be in m.get(var.json_block_event, []):
            ts = be.get(var.json_timestamp)
            if not ts:
                continue

            block_id = f"block_{user_id}_{norm(ts)}"

            rows.append({
                var.col_block_id: block_id,
                var.col_block_timestamp: ts,
                var.col_user_id: user_id,
                var.col_match_id: match_id,
                var.col_block_type: be.get(var.json_block_type),
            })

    if rows:
        supabase.table(var.table_blocks).upsert(rows).execute()


# --------------------------------------------------
# LIKES
# --------------------------------------------------
def likes_ingest(json_data, user_id):

    rows = []

    for m in json_data.get(var.json_matches, []):
        match_id = None
        match_event = m.get(var.json_match_event)
        if match_event:
            ts_match = match_event[0].get(var.json_timestamp)
            if ts_match:
                match_id = f"match_{user_id}_{norm(ts_match)}"

        for outer in m.get(var.json_like_key, []):
            for inner in outer.get(var.json_like_key, []):
                ts = inner.get(var.json_timestamp)
                if not ts:
                    continue

                like_id = f"like_{user_id}_{norm(ts)}"

                rows.append({
                    var.col_like_id: like_id,
                    var.col_like_timestamp: ts,
                    var.col_user_id: user_id,
                    var.col_match_id: match_id,
                })

    if rows:
        supabase.table(var.table_likes).upsert(rows).execute()


# --------------------------------------------------
# MESSAGES (TEXT + VOICE)
# --------------------------------------------------
def messages_ingest(json_data, user_id):

    rows = {}
    matches = json_data.get(var.json_matches, [])

    # voice lookup
    voice_map = {}
    for m in matches:
        for vn in m.get(var.json_voice_notes, []):
            ts = vn.get(var.json_timestamp)
            url = vn.get(var.json_media_url)
            if ts and url:
                voice_map[ts] = url

    for m in matches:
        match_id = None
        match_event = m.get(var.json_match_event)
        if match_event:
            ts_match = match_event[0].get(var.json_timestamp)
            if ts_match:
                match_id = f"match_{user_id}_{norm(ts_match)}"

        # chat messages
        for chat in m.get(var.json_chats, []):
            ts = chat.get(var.json_timestamp)
            if not ts:
                continue

            msg_id = f"message_{user_id}_{norm(ts)}"
            existing = rows.get(msg_id, {})

            rows[msg_id] = {
                var.col_message_id: msg_id,
                var.col_message_timestamp: ts,
                var.col_user_id: user_id,
                var.col_match_id: match_id,
                var.col_like_id: existing.get(var.col_like_id),
                var.col_message_body: chat.get(var.json_body)
                    or existing.get(var.col_message_body),
                var.col_message_voicenote_url: (
                    voice_map.get(ts)
                    or existing.get(var.col_message_voicenote_url)
                ),
            }

        # like comments
        for outer in m.get(var.json_like_key, []):
            for inner in outer.get(var.json_like_key, []):
                ts = inner.get(var.json_timestamp)
                comment = inner.get(var.json_comment)
                if not ts or not comment:
                    continue

                msg_id = f"message_{user_id}_{norm(ts)}"
                like_id = f"like_{user_id}_{norm(ts)}"
                existing = rows.get(msg_id, {})

                rows[msg_id] = {
                    var.col_message_id: msg_id,
                    var.col_message_timestamp: ts,
                    var.col_user_id: user_id,
                    var.col_match_id: match_id,
                    var.col_like_id: like_id,
                    var.col_message_body: comment
                        or existing.get(var.col_message_body),
                    var.col_message_voicenote_url: (
                        voice_map.get(ts)
                        or existing.get(var.col_message_voicenote_url)
                    ),
                }

    if rows:
        supabase.table(var.table_messages).upsert(list(rows.values())).execute()


# --------------------------------------------------
# USER PROFILE
# --------------------------------------------------
def user_profile_ingest(json_data, user_id):

    user = json_data.get(var.json_user, {})
    selfie_verification = json_data.get(var.json_selfie_verification)

    current = (
        supabase.table(var.table_user_profile)
        .select(var.col_upload_count)
        .eq(var.col_user_id, user_id)
        .maybe_single()
        .execute()
    )

    upload_count = (
        (current.data[var.col_upload_count] if current and current.data else 0)
        + 1
    )

    row = {
        var.col_user_id: user_id,
        var.col_upload_count: upload_count,
        var.col_preferences: user.get(var.json_user_preferences) or {},
        var.col_location: user.get(var.json_user_location) or {},
        var.col_identity: user.get(var.json_user_identity) or {},
        var.col_profile: user.get(var.json_user_profile) or {},
        var.col_account: user.get(var.json_user_account) or {},
        var.col_selfie_verification: selfie_verification or {},
    }

    supabase.table(var.table_user_profile).upsert(
        row, on_conflict=var.col_user_id
    ).execute()








# --------------------------------------------------
# MEDIA
# --------------------------------------------------
def media_ingest(json_data, user_id):

    rows = []

    for item in json_data.get(var.json_media, []):
        if not isinstance(item, dict):
            continue

        url = item.get(var.json_media_url)
        if not url:
            continue

        media_type = item.get(var.json_media_type)
        from_social = item.get(var.json_media_social, False)
        prompt = item.get(var.json_media_prompt)

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
            var.col_media_prompt: prompt,
            var.col_user_id:      user_id,
        })

    if rows:
        supabase.table(var.table_media).upsert(rows).execute()





def prompts_ingest(json_data, user_id):

    rows = []

    prompts = (
        json_data.get(var.json_prompts, [])
        if isinstance(json_data, dict)
        else (json_data or [])
    )

    for p in prompts:
        if not isinstance(p, dict):
            continue

        prompt_raw_id = p.get(var.json_prompt_id)
        created = p.get(var.json_prompt_created)
        if prompt_raw_id is None or not created:
            continue

        updated = p.get(var.json_prompt_updated) or created
        prompt_id = f"prompt_{user_id}_{prompt_raw_id}_{norm(created)}"

        rows.append({
            var.col_prompt_id:         prompt_id,
            var.col_user_id:           user_id,
            var.col_prompt_type:       p.get(var.json_prompt_type),
            var.col_prompt_label:      p.get(var.json_prompt_label),
            var.col_prompt_text:       p.get(var.json_prompt_text),   # ← your original logic
            var.col_prompt_created_ts: created,
            var.col_prompt_updated_ts: updated,
            var.col_prompt_options:    p.get(var.json_options),
            var.col_prompt_media_url:  p.get(var.json_prompt_media_url),
        })

    if rows:
        supabase.table(var.table_prompts).upsert(rows).execute()




# --------------------------------------------------
# SUBSCRIPTIONS
# --------------------------------------------------
def subscriptions_ingest(json_data, user_id):

    rows = []

    for s in json_data.get(var.json_subscriptions, []):
        sid = s.get(var.json_sub_id)
        start = s.get(var.json_sub_start_date)
        if not sid or not start:
            continue

        sub_id = f"subscription_{user_id}_{sid}_{norm(start)}"

        rows.append({
            var.col_subscription_id:       sub_id,
            var.col_subscription_start_ts: start,
            var.col_subscription_end_ts:   s.get(var.json_sub_end_date),
            var.col_subscription_price:    s.get(var.json_sub_price),
            var.col_subscription_currency: s.get(var.json_sub_currency),
            var.col_subscription_type:     s.get(var.json_sub_type),
            var.col_user_id:               user_id,
        })

    if rows:
        supabase.table(var.table_subscriptions).upsert(rows).execute()








def store_raw_export_zip(zip_path, user_id):
    """
    Upload a slimmed raw export ZIP to Supabase Storage.
    Excludes `media/` folder and any `index.html`, keeps everything else (including media.json).
    Returns (object_path, sha256).
    """

    buf = io.BytesIO()

    with zipfile.ZipFile(zip_path, "r") as zin, zipfile.ZipFile(
        buf, "w", compression=zipfile.ZIP_DEFLATED
    ) as zout:
        for info in zin.infolist():
            name = info.filename

            # drop the massive media folder only
            if name.startswith("media/") or name.startswith("media\\"):
                continue

            # drop any index.html (root or nested)
            base = name.split("/")[-1].split("\\")[-1]
            if base.lower() == "index.html":
                continue

            zout.writestr(info, zin.read(info.filename))

    slim_bytes = buf.getvalue()

    sha = hashlib.sha256(slim_bytes).hexdigest()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    object_path = f"{user_id}/{ts}_{sha}.zip"

    supabase_admin.storage.from_(var.bucket_raw_exports).upload(
        object_path,
        slim_bytes,
        file_options={
            "content-type": "application/zip",
            "upsert": "false",
        },
    )

    return object_path, sha










def delete_my_data(user_id):
    tables = [
        var.table_messages,        # references likes + matches
        var.table_likes,           # references matches
        var.table_blocks,          # references matches
        var.table_matches,         # parent
        var.table_media,
        var.table_prompts,
        var.table_subscriptions,
        var.table_user_profile,    # root record
    ]

    for table in tables:
        supabase.table(table).delete().eq(var.col_user_id, user_id).execute()
