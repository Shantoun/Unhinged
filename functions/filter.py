import numpy as np
import pandas as pd
import streamlit as st
import variables as var
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import re
from forex_python.converter import CurrencyRates

operators_numeric = ['=', '≠', '≥', '≤', 'Between']
operators_text = ['=', '≠', 'Contains', 'Doesn\'t Contain', 'Starts with', 'Ends with']
operators_date = ['Window', '=', '≥', '≤', 'Between']

color_dot_separator = '#C23331'

######################################## detect column type
def detect_column_type(df, col, return_type="operator"):
    series = df[col].dropna()

    if pd.api.types.is_numeric_dtype(series):
        col_type = "numeric"
    elif pd.api.types.is_datetime64_any_dtype(series):
        col_type = "date"
    else:
        try:
            parsed = pd.to_datetime(series, errors="coerce")
            col_type = "date" if parsed.notna().mean() > 0.8 else "text"
        except Exception:
            col_type = "text"

    mapping = {
        "numeric": {"operators": operators_numeric, "label": "Numeric"},
        "date": {"operators": operators_date, "label": "Date"},
        "text": {"operators": operators_text, "label": "Text"},
    }

    if return_type == "operator":
        return mapping[col_type]["operators"]
    elif return_type == "label":
        return mapping[col_type]["label"]
    else:
        raise ValueError("return_type must be 'operator' or 'label'")




######################################## smart number input
def smart_number_input(df, col, slot, label="Value", default="min"):
    series = pd.to_numeric(df[col], errors="coerce").dropna()
    if series.empty:
        st.warning("No numeric values found.")
        return None

    min_val = float(series.min())
    max_val = float(series.max())
    value_range = max_val - min_val if max_val != min_val else 1.0

    step = float(10 ** (np.floor(np.log10(value_range)) - 2)) if value_range > 0 else 0.01
    decimals = int(max(0, -np.floor(np.log10(step))))
    fmt = f"%.{decimals}f"
    value = max_val if default == "max" else min_val

    with slot:
        val = st.number_input(
            label,
            min_value=min_val,
            max_value=max_val,
            step=step,
            format=fmt,
            value=value,
            label_visibility="hidden",
            key=f"{label}_{col}"
        )
    return val



######################################## between 
def between(df, col, slot, layout="row"):
    if layout == "row":
        c1, c_and, c2 = slot.columns([20, 1, 20])
        with c1:
            vmin = smart_number_input(df, col, c1, label="Min", default="min")
        with c_and:
            st.markdown("<p style='text-align:center; margin-top: 2rem;'>&</p>", unsafe_allow_html=True)
        with c2:
            vmax = smart_number_input(df, col, c2, label="Max", default="max")
    else:
        vmin = smart_number_input(df, col, slot, label="Min", default="min")
        vmax = smart_number_input(df, col, slot, label="Max", default="max")

    if vmax < vmin:
        vmax = vmin
    return vmin, vmax



######################################## value input
def value_input(df, filter_col, operator, slot, allow_future=False, layout="row"):
    col_type = detect_column_type(df, filter_col, "label")

    if col_type == "Numeric":
        if operator == "Between":
            return between(df, filter_col, slot, layout)
        else:
            return smart_number_input(df, filter_col, slot, default="min")

    elif col_type == "Text":
        with slot:
            if operator == "=":
                val = st.multiselect(
                    "Select values",
                    options=df[filter_col].dropna().unique().tolist(),
                    default=None,
                    label_visibility="hidden",
                    key=f"text_{filter_col}",
                )
            else:
                val = st.text_input(
                    "Enter text",
                    value="",
                    label_visibility="hidden",
                    key=f"text_{filter_col}",
                )
        return val

    elif col_type == "Date":
        with slot:
            # ---- Between ----
            if operator == "Between":
                if not df[filter_col].isna().all():
                    min_date = pd.to_datetime(df[filter_col].min(), errors="coerce")
                    max_date = pd.to_datetime(df[filter_col].max(), errors="coerce")
                    default_range = (min_date.date(), max_date.date())
                else:
                    default_range = (None, None)

                date_range = st.date_input(
                    "Select date range",
                    value=default_range,
                    label_visibility="hidden",
                    key=f"date_between_{filter_col}",
                )
                if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
                    vmin, vmax = date_range
                else:
                    vmin = vmax = date_range
                return (vmin, vmax)

            # ---- Window ----
            elif operator == "Window":
                options = [
                    "today", "yesterday", "this week", "last week",
                    "this month", "last month", "this quarter", "last quarter",
                    "this year", "last year", "last 7 days", "last 30 days", "last 90 days",
                ]
                if allow_future:
                    options += [
                        "next week", "next month", "next quarter", "next year",
                        "next 30 days", "next 90 days",
                    ]
                val = st.multiselect(
                    "Select or type window",
                    options=options,
                    default=None,
                    accept_new_options=True,
                    label_visibility="hidden",
                    key=f"window_{filter_col}",
                    placeholder="Type 'last x days' or pick preset",
                    help="You can type custom windows like 'last 2 quarters'.",
                )
                if val:
                    val = [v.strip().lower() for v in val]
                return val

            # ---- Single Date ----
            else:
                if not df[filter_col].isna().all():
                    default_date = pd.to_datetime(df[filter_col].max(), errors="coerce").date()
                else:
                    default_date = None

                val = st.date_input(
                    "Select date",
                    value=default_date,
                    label_visibility="hidden",
                    key=f"date_single_{filter_col}",
                )
                return val



######################################## add_filter (OVERWRITES NOW)
def add_filter(column, operator, value, key, df):
    key_name = f"filters_{key}"
    
    def parse_date(v):
        if isinstance(v, (list, tuple)):
            return [parse_date(x) for x in v]
        if isinstance(v, (pd.Timestamp, type(pd.Timestamp.now().date()))):
            return pd.to_datetime(v, errors="coerce")
        if isinstance(v, str):
            v = v.strip().replace("/", "-")
            return pd.to_datetime(v, errors="coerce")
        return v

    col_type = detect_column_type(df, column, "label")

    # ---------- validation ----------
    if operator == "Between":
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            st.toast(f"'{column}' filter ignored (invalid range)", icon="⚠️")
            return

        if col_type == "Date":
            value = parse_date(value)
            if any(pd.isna(v) for v in value):
                st.toast(f"'{column}' filter ignored (invalid date range)", icon="⚠️")
                return

        elif col_type == "Numeric":
            try:
                value = [float(v) for v in value]
            except Exception:
                st.toast(f"'{column}' filter ignored (invalid number range)", icon="⚠️")
                return

        else:  # Text
            value = [str(v).strip() for v in value if str(v).strip()]

    elif operator in ["=", "≥", "≤", "≠"]:
        if isinstance(value, (list, tuple)) and len(value) == 1:
            value = value[0]

        if col_type == "Date":
            if not isinstance(value, (pd.Timestamp, type(pd.Timestamp.now().date()))):
                parsed = parse_date(value)
                if isinstance(parsed, pd.Timestamp) and not pd.isna(parsed):
                    value = parsed
                else:
                    st.toast(f"'{column}' filter ignored (invalid date)", icon="⚠️")
                    return

        elif col_type == "Numeric":
            try:
                value = float(value)
            except Exception:
                st.toast(f"'{column}' filter ignored (invalid number)", icon="⚠️")
                return

        else:  # Text
            if isinstance(value, (list, tuple)):
                value = [str(v).strip() for v in value if v]
            else:
                value = str(value).strip()
            if not value:
                st.toast(f"'{column}' filter ignored (empty value)", icon="⚠️")
                return

    elif operator == "Window":
        if not value or not isinstance(value, (list, tuple)):
            st.toast(f"'{column}' filter ignored (invalid window)", icon="⚠️")
            return

        valid_patterns = [
            r"^(today|yesterday)$",
            r"^(this|last|next)\s+(day|week|month|quarter|year)s?$",
            r"^(last|next)\s+\d+\s+(day|week|month|quarter|year)s?$",
            r"^\d{4}$",
            r"^q[1-4](\s+\d{4})?$",
            r"^week\s+\d{1,2}(\s+\d{4})?$",
            r"^[a-zA-Z]+(\s+\d{4})?$",
        ]
        value = [
            v.strip().lower()
            for v in value
            if isinstance(v, str)
            and any(re.match(p, v.strip().lower()) for p in valid_patterns)
        ]
        if not value:
            st.toast(f"'{column}' filter ignored (unrecognized window)", icon="⚠️")
            return

    # OVERWRITE - only keep the latest filter
    st.session_state[key_name] = [
        {"column": column, "operator": operator, "value": value}
    ]




######################################## apply_filters
def apply_filters(df, key):
    key_name = f"filters_{key}"
    if key_name not in st.session_state or not st.session_state[key_name]:
        return df

    filtered_df = df.copy()

    for f in st.session_state[key_name]:
        col = f["column"]
        op_ = f["operator"]
        value = f["value"]

        if col not in filtered_df.columns:
            continue

        # ========== RANGES OPERATOR ==========
        if op_ == "Ranges":
            filtered_df[col] = pd.to_datetime(filtered_df[col], errors="coerce")
            filtered_df = filtered_df.loc[filtered_df[col].notna()]
            
            # Make sure the column is timezone-naive
            if filtered_df[col].dt.tz is not None:
                filtered_df[col] = filtered_df[col].dt.tz_localize(None)
            
            mask = pd.Series(False, index=filtered_df.index)
            
            for start_ts, end_ts in value:
                start_ts = pd.to_datetime(start_ts, errors="coerce")
                end_ts = pd.to_datetime(end_ts, errors="coerce")
                
                # Make timestamps timezone-naive to match
                if hasattr(start_ts, 'tz_localize'):
                    if start_ts.tz is not None:
                        start_ts = start_ts.tz_localize(None)
                if hasattr(end_ts, 'tz_localize'):
                    if end_ts.tz is not None:
                        end_ts = end_ts.tz_localize(None)
                
                # Handle missing dates
                if pd.isna(start_ts) and pd.isna(end_ts):
                    continue  # skip if both are missing
                elif pd.isna(start_ts):
                    # No start date = less than or equal to end
                    cond = filtered_df[col] <= end_ts
                elif pd.isna(end_ts):
                    # No end date = greater than or equal to start
                    cond = filtered_df[col] >= start_ts
                else:
                    # Both dates present = between
                    cond = (filtered_df[col] >= start_ts) & (filtered_df[col] <= end_ts)
                
                mask |= cond
            
            filtered_df = filtered_df[mask]
            continue

        # --- detect column type ---
        col_type = detect_column_type(filtered_df, col, "label")

        # --- coerce type properly ---
        if col_type == "Date":
            filtered_df[col] = pd.to_datetime(filtered_df[col], errors="coerce")
            filtered_df = filtered_df.loc[filtered_df[col].notna()]
        elif col_type == "Numeric":
            filtered_df[col] = pd.to_numeric(filtered_df[col], errors="coerce")
            filtered_df = filtered_df.loc[filtered_df[col].notna()]
        else:
            filtered_df[col] = filtered_df[col].astype(str)

        # ---------- operator logic ----------
        try:
            # -------- BETWEEN --------
            if op_ == "Between" and isinstance(value, (tuple, list)) and len(value) == 2:
                v0, v1 = value

                if col_type == "Date":
                    v0 = pd.to_datetime(v0, errors="coerce")
                    v1 = pd.to_datetime(v1, errors="coerce")
                    filtered_df = filtered_df[
                        (filtered_df[col] >= v0) & (filtered_df[col] <= v1)
                    ]

                elif col_type == "Numeric":
                    v0, v1 = float(v0), float(v1)
                    filtered_df = filtered_df[
                        (filtered_df[col] >= v0) & (filtered_df[col] <= v1)
                    ]

                else:  # text → lexical compare
                    filtered_df = filtered_df[
                        filtered_df[col].between(str(v0), str(v1))
                    ]

            # -------- EQUALITY / COMPARISON --------
            elif op_ in ["=", "≥", "≤", "≠"]:
                if isinstance(value, (list, tuple)):
                    # allow multi-selects for text columns
                    if col_type == "Text":
                        value = [str(v).strip() for v in value if str(v).strip()]
                    elif len(value) == 1:
                        value = value[0]
            
                # --- normalize according to column type ---
                if col_type == "Date":
                    value = pd.to_datetime(value, errors="coerce")
                elif col_type == "Numeric":
                    value = float(value)
                else:  # text / categorical
                    value = [value] if not isinstance(value, list) else value
                    value = [str(v) for v in value]
            
                # --- comparison logic ---
                if op_ == "=":
                    if col_type == "Text" and isinstance(value, list):
                        filtered_df = filtered_df[filtered_df[col].isin(value)]
                    else:
                        filtered_df = filtered_df[filtered_df[col] == value]
                elif op_ == "≥":
                    filtered_df = filtered_df[filtered_df[col] >= value]
                elif op_ == "≤":
                    filtered_df = filtered_df[filtered_df[col] <= value]
                elif op_ == "≠":
                    if col_type == "Text" and isinstance(value, list):
                        filtered_df = filtered_df[~filtered_df[col].isin(value)]
                    else:
                        filtered_df = filtered_df[filtered_df[col] != value]

            # -------- TEXT SEARCH --------
            elif op_ == "Contains":
                filtered_df = filtered_df[
                    filtered_df[col].astype(str).str.contains(str(value), case=False, na=False)
                ]

            elif op_ == "Doesn't Contain":
                filtered_df = filtered_df[
                    ~filtered_df[col].astype(str).str.contains(str(value), case=False, na=False)
                ]

            elif op_ == "Starts with":
                filtered_df = filtered_df[
                    filtered_df[col].astype(str).str.startswith(str(value), na=False)
                ]

            elif op_ == "Ends with":
                filtered_df = filtered_df[
                    filtered_df[col].astype(str).str.endswith(str(value), na=False)
                ]


            elif op_ == "Window":
                filtered_df[col] = pd.to_datetime(filtered_df[col], errors="coerce")
                filtered_df = filtered_df.loc[filtered_df[col].notna()]

                # ---------- always use dataset max ----------
                dataset_max = pd.to_datetime(df[col], errors="coerce").max()
                if pd.isna(dataset_max):
                    # no date info — skip filtering for this column
                    continue
                now = dataset_max.normalize()

                mask = pd.Series(False, index=filtered_df.index)

                for v in value if isinstance(value, (list, tuple)) else [value]:
                    if not v:
                        continue
                    txt = str(v).lower().strip()
                    valid_window = False

                    # ---------- explicit keywords ----------
                    if txt == "today":
                        valid_window = True
                        cond = filtered_df[col].dt.normalize() == now
                    elif txt == "yesterday":
                        valid_window = True
                        cond = filtered_df[col].dt.normalize() == (now - pd.Timedelta(days=1))
                    elif txt == "this week":
                        valid_window = True
                        start = now - pd.Timedelta(days=now.weekday())
                        end = start + pd.Timedelta(days=6)
                        cond = filtered_df[col].between(start, end)
                    elif txt == "last week":
                        valid_window = True
                        start = now - pd.Timedelta(days=now.weekday() + 7)
                        end = start + pd.Timedelta(days=6)
                        cond = filtered_df[col].between(start, end)
                    elif txt == "next week":
                        valid_window = True
                        start = now + pd.Timedelta(days=7 - now.weekday())
                        end = start + pd.Timedelta(days=6)
                        cond = filtered_df[col].between(start, end)
                    elif txt == "this month":
                        valid_window = True
                        start = now.replace(day=1)
                        end = (start + pd.DateOffset(months=1)) - pd.Timedelta(days=1)
                        cond = filtered_df[col].between(start, end)
                    elif txt == "last month":
                        valid_window = True
                        start = (now.replace(day=1) - pd.DateOffset(months=1)).replace(day=1)
                        end = (start + pd.DateOffset(months=1)) - pd.Timedelta(days=1)
                        cond = filtered_df[col].between(start, end)
                    elif txt == "next month":
                        valid_window = True
                        start = (now.replace(day=1) + pd.DateOffset(months=1))
                        end = (start + pd.DateOffset(months=1)) - pd.Timedelta(days=1)
                        cond = filtered_df[col].between(start, end)
                    elif txt == "this quarter":
                        valid_window = True
                        q = (now.month - 1) // 3 + 1
                        start = pd.Timestamp(year=now.year, month=3 * (q - 1) + 1, day=1)
                        end = (start + pd.DateOffset(months=3)) - pd.Timedelta(days=1)
                        cond = filtered_df[col].between(start, end)
                    elif txt == "last quarter":
                        valid_window = True
                        q = (now.month - 1) // 3
                        year = now.year if q > 0 else now.year - 1
                        q = q if q > 0 else 4
                        start = pd.Timestamp(year=year, month=3 * (q - 1) + 1, day=1)
                        end = (start + pd.DateOffset(months=3)) - pd.Timedelta(days=1)
                        cond = filtered_df[col].between(start, end)
                    elif txt == "next quarter":
                        valid_window = True
                        q = (now.month - 1) // 3 + 2
                        year = now.year + (1 if q > 4 else 0)
                        q = ((q - 1) % 4) + 1
                        start = pd.Timestamp(year=year, month=3 * (q - 1) + 1, day=1)
                        end = (start + pd.DateOffset(months=3)) - pd.Timedelta(days=1)
                        cond = filtered_df[col].between(start, end)
                    elif txt == "this year":
                        valid_window = True
                        start = pd.Timestamp(year=now.year, month=1, day=1)
                        end = pd.Timestamp(year=now.year, month=12, day=31)
                        cond = filtered_df[col].between(start, end)
                    elif txt == "last year":
                        valid_window = True
                        y = now.year - 1
                        start = pd.Timestamp(year=y, month=1, day=1)
                        end = pd.Timestamp(year=y, month=12, day=31)
                        cond = filtered_df[col].between(start, end)
                    elif txt == "next year":
                        valid_window = True
                        y = now.year + 1
                        start = pd.Timestamp(year=y, month=1, day=1)
                        end = pd.Timestamp(year=y, month=12, day=31)
                        cond = filtered_df[col].between(start, end)

                    # ---------- relative patterns ----------
                    elif re.match(r"(last|next)\s+\d+\s+(day|week|month|quarter|year)s?", txt):
                        valid_window = True
                        m = re.match(r"(last|next)\s+(\d+)\s+(day|week|month|quarter|year)s?", txt)
                        direction, n, unit = m.groups()
                        n = int(n)
                        mult = -1 if direction == "last" else 1
                        offset = {
                            "day": pd.DateOffset(days=n * mult),
                            "week": pd.DateOffset(weeks=n * mult),
                            "month": pd.DateOffset(months=n * mult),
                            "quarter": pd.DateOffset(months=3 * n * mult),
                            "year": pd.DateOffset(years=n * mult),
                        }[unit]
                        start = now + (offset if direction == "last" else pd.DateOffset())
                        end = now + (offset if direction == "next" else pd.DateOffset())
                        cond = filtered_df[col].between(min(start, end), max(start, end))

                    # ---------- explicit date formats ----------
                    elif re.match(r"week\s+\d{1,2}(\s+\d{4})?", txt):
                        valid_window = True
                        m = re.match(r"week\s+(\d{1,2})(?:\s+(\d{4}))?", txt)
                        week_num, year = int(m.group(1)), int(m.group(2) or now.year)
                        start = pd.Timestamp.fromisocalendar(year, week_num, 1)
                        end = start + pd.Timedelta(days=6)
                        cond = filtered_df[col].between(start, end)

                    elif re.match(r"(q[1-4])(\s+\d{4})?", txt):
                        valid_window = True
                        m = re.match(r"q([1-4])(?:\s+(\d{4}))?", txt)
                        q, year = int(m.group(1)), int(m.group(2) or now.year)
                        start = pd.Timestamp(year=year, month=3 * (q - 1) + 1, day=1)
                        end = (start + pd.DateOffset(months=3)) - pd.Timedelta(days=1)
                        cond = filtered_df[col].between(start, end)

                    elif re.match(r"^[a-zA-Z]+(\s+\d{4})?$", txt, re.IGNORECASE):  # month name or month+year
                        valid_window = True
                        try:
                            parts = txt.strip().split()
                            month_name = parts[0].capitalize()
                            year = int(parts[1]) if len(parts) > 1 else now.year
                    
                            # try both full and abbreviated month formats
                            mnum = None
                            for fmt in ("%B", "%b"):
                                parsed = pd.to_datetime(month_name, format=fmt, errors="coerce")
                                if not pd.isna(parsed):
                                    mnum = parsed.month
                                    break
                    
                            if mnum is not None:
                                start = pd.Timestamp(year=year, month=mnum, day=1)
                                end = (start + pd.DateOffset(months=1)) - pd.Timedelta(days=1)
                                cond = filtered_df[col].between(start, end)
                            else:
                                cond = pd.Series(False, index=filtered_df.index)
                        except Exception:
                            cond = pd.Series(False, index=filtered_df.index)

                    elif re.match(r"^\d{4}$", txt):  # just year
                        valid_window = True
                        y = int(txt)
                        start = pd.Timestamp(year=y, month=1, day=1)
                        end = pd.Timestamp(year=y, month=12, day=31)
                        cond = filtered_df[col].between(start, end)

                    else:
                        cond = pd.Series(False, index=filtered_df.index)

                    if valid_window:
                        mask |= cond
                    else:
                        st.toast(f"{v} not recognized as a valid date window", icon="⚠️")

                filtered_df = filtered_df[mask]

        except Exception:
            return filtered_df.iloc[0:0]

    return filtered_df.copy()



######################################## filter_ui
def filter_ui(df, filterable_columns, allow_future_windows=False, key=None, layout="row", user_id=None):
    key_name = f"filters_{key}"
    if key_name not in st.session_state:
        st.session_state[key_name] = []
    
    # Fetch subscription ranges if user_id provided
    subscription_ranges = None
    if user_id:
        from functions.authentification import supabase
        
        subs_df = pd.DataFrame(
            supabase.table(var.table_subscriptions).select("*").eq(var.col_user_id, user_id).execute().data or []
        )
        
        if not subs_df.empty:
            subs_df['start_timestamp'] = pd.to_datetime(subs_df['start_timestamp'], errors='coerce')
            subs_df['end_timestamp'] = pd.to_datetime(subs_df['end_timestamp'], errors='coerce')
            subs_df = subs_df.sort_values('start_timestamp')
            
            # Separate first
            has_tag = subs_df['tag'].notna() & (subs_df['tag'] != '')
            user_created_rows = subs_df[has_tag].copy()
            hinge_subs = subs_df[~has_tag].copy()
            
            # Group hinge renewals FIRST (before mixing with user-created)
            grouped_rows = []
            
            for idx, row in hinge_subs.iterrows():
                if (grouped_rows and 
                    grouped_rows[-1]['end'] == row['start_timestamp'] and
                    grouped_rows[-1].get('duration') == row.get('subscription_duration')):
                    
                    # Merge renewal - take MOST RECENT price and currency
                    prev = grouped_rows[-1]
                    prev['end'] = row['end_timestamp']
                    prev['price'] = row.get('price')
                    prev['currency'] = row.get('currency')
                    prev['count'] = prev.get('count', 1) + 1
                    # Update name with most recent price
                    prev['name'] = f"{row.get('currency')} {row.get('price')} - {row.get('subscription_duration')}"
                else:
                    # New group
                    grouped_rows.append({
                        'name': f"{row.get('currency')} {row.get('price')} - {row.get('subscription_duration')}",
                        'start': row['start_timestamp'],
                        'end': row['end_timestamp'],
                        'currency': row.get('currency'),
                        'price': row.get('price'),
                        'duration': row.get('subscription_duration'),
                        'count': 1,
                        'is_tagged': False
                    })
            
            # Add user-created ranges
            for _, row in user_created_rows.iterrows():
                grouped_rows.append({
                    'name': row['tag'],
                    'start': row['start_timestamp'],
                    'end': row['end_timestamp'],
                    'is_tagged': True
                })
            
            # Sort by start date
            grouped_rows.sort(key=lambda x: (
                x['start'].tz_localize(None) if hasattr(x['start'], 'tz') and x['start'].tz is not None 
                else x['start']
            ) if pd.notna(x['start']) else pd.Timestamp.min)
                        
            # Build display dataframe
            subscription_ranges = pd.DataFrame({
                'Name': [r['name'] for r in grouped_rows],
                'Start': [r['start'].strftime('%b %d, %Y') if pd.notna(r['start']) else '' for r in grouped_rows],
                'End': [r['end'].strftime('%b %d, %Y') if pd.notna(r['end']) else '' for r in grouped_rows],
                '_start_ts': [r['start'] for r in grouped_rows],
                '_end_ts': [r['end'] for r in grouped_rows]
            })
    
    # Mode selection (only show if we have subscription ranges)
    if subscription_ranges is not None:
        mode = st.radio("Filter Mode", ["Ranges", "Custom Filter"], horizontal=True, key=f"{key}_mode", label_visibility="collapsed")
    else:
        mode = "Custom Filter"
    
    # ========== RANGES MODE ==========
    if subscription_ranges is not None and mode == "Ranges":
        st.dataframe(
            subscription_ranges[['Name', 'Start', 'End']],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row",
            key=f"{key}_range_table"
        )
        
        # Add the same 2-button layout as Filter tab
        b1, b2 = st.columns(2)
        with b1:
            clear_clicked_ranges = st.button("Clear All", use_container_width=True, key=f"{key}_clear_ranges")
        with b2:
            commit_clicked_ranges = st.button("Commit", type="primary", use_container_width=True, key=f"{key}_commit_ranges")
        
        if commit_clicked_ranges:
            selected_indices = st.session_state.get(f"{key}_range_table", {}).get("selection", {}).get("rows", [])
            
            if selected_indices:
                # Build OR filter from selected ranges
                filter_col = filterable_columns[0]
                selected_ranges = subscription_ranges.iloc[selected_indices]
                
                # Store as special "ranges" filter
                st.session_state[key_name] = [{
                    "column": filter_col,
                    "operator": "Ranges",
                    "value": selected_ranges[['_start_ts', '_end_ts']].values.tolist(),
                    "display": selected_ranges['Name'].tolist()
                }]
            else:
                st.session_state[key_name] = []
        
        if clear_clicked_ranges:
            st.session_state[key_name] = []
    
    # ========== CUSTOM FILTER MODE ==========
    elif mode == "Custom Filter":
        placeholder = st.container()
        
        if layout == "row":
            with placeholder:
                filter_col = filterable_columns[0]
                operator_select, value_select = st.columns(2)
                
                if df[filter_col].dropna().empty:
                    return df, None
                
                operators = detect_column_type(df, filter_col)
                col_type = detect_column_type(df, filter_col, "label")
                with operator_select:
                    operator = st.selectbox("Operator", operators, key=f"{key}_op_row", label_visibility="hidden")
                from functions.filter import value_input
                value = value_input(
                    df, filter_col, operator, value_select,
                    allow_future=allow_future_windows if col_type == "Date" else False,
                    layout="row"
                )
        else:
            with placeholder:
                filter_col = filterable_columns[0]
            
                if df[filter_col].dropna().empty:
                    return df, None
                
                operators = detect_column_type(df, filter_col)
                col_type = detect_column_type(df, filter_col, "label")
                operator = st.selectbox("Operator", operators, key=f"{key}_op_col", label_visibility="hidden")
                from functions.filter import value_input
                value = value_input(
                    df, filter_col, operator, st.container(),
                    allow_future=allow_future_windows if col_type == "Date" else False,
                    layout="column"
                )
        
        b1, b2 = st.columns(2)
        with b1:
            clear_clicked = st.button("Clear All", use_container_width=True, key=f"{key}_clear")
        with b2:
            commit_clicked = st.button("Commit", type="primary", use_container_width=True, key=f"{key}_commit")
        
        if commit_clicked:
            add_filter(filter_col, operator, value, key, df)
        if clear_clicked:
            st.session_state[key_name] = []
    
    # ========== APPLY FILTERS ==========
    from functions.filter import apply_filters
    filtered_df = apply_filters(df, key)
    
    # ========== BUILD FILTER TEXT ==========
    if st.session_state[key_name]:
        f = st.session_state[key_name][0]
        
        if f["operator"] == "Ranges":
            # Show range names
            range_names = f.get("display", [])
            filter_text = f"Date Ranges: {', '.join(range_names)}"
        else:
            filter_text = f"{f['column']} {f['operator']} {f['value']}"
    else:
        filter_col = filterable_columns[0]
        try:
            min_date = pd.to_datetime(df[filter_col], errors='coerce').min()
            max_date = pd.to_datetime(df[filter_col], errors='coerce').max()
            if pd.isna(min_date) or pd.isna(max_date):
                filter_text = None
            else:
                filter_text = f"Date Between {min_date.strftime('%b %d, %Y')} and {max_date.strftime('%b %d, %Y')}"
        except:
            filter_text = None
    
    return filtered_df, filter_text

######################################## get_window_selected
def get_window_selected(key):
    """Return the active Window filter value (e.g. 'this month', 'last 7 days')"""
    filters = st.session_state.get(f"filters_{key}", [])
    for f in filters:
        if f["operator"] == "Window" and f["value"]:
            return f["value"][0].lower()
    return None



######################################## except date
def apply_filters_except_date(df, key, date_col):
    """Apply ALL non-date filters using AND logic by reusing apply_filters"""
    key_name = f"filters_{key}"
    full_list = st.session_state.get(key_name, [])
    non_date_filters = [f for f in full_list if f.get("column") != date_col]
    
    if not non_date_filters:
        return df
    
    # use a temp key so we don't overwrite the real filters
    temp_key = f"{key}__temp_non_date"
    st.session_state[f"filters_{temp_key}"] = non_date_filters
    try:
        from functions.filter import apply_filters
        out = apply_filters(df, temp_key)
    finally:
        # clean up temp key to avoid lingering state
        if f"filters_{temp_key}" in st.session_state:
            del st.session_state[f"filters_{temp_key}"]
    return out


######################################## only date (intersection-based)
def apply_date_filters(df, key, date_col, source_date_col=None):
    """Apply date filters to a different column name"""
    key_name = f"filters_{key}"
    full_list = st.session_state.get(key_name, [])
    
    # if source_date_col provided, grab filters from that column instead
    filter_col = source_date_col if source_date_col else date_col
    date_filters = [f for f in full_list if f.get("column") == filter_col]
    
    if not date_filters:
        return df
    
    # replace column name to match target df
    date_filters = [
        {**f, "column": date_col} for f in date_filters
    ]
    
    temp_key = f"{key}__temp_date_only"
    st.session_state[f"filters_{temp_key}"] = date_filters
    try:
        from functions.filter import apply_filters
        out = apply_filters(df, temp_key)
    finally:
        if f"filters_{temp_key}" in st.session_state:
            del st.session_state[f"filters_{temp_key}"]
    return out
