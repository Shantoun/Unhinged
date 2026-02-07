import numpy as np
import pandas as pd
import streamlit as st
import re
from datetime import timedelta
from dateutil.relativedelta import relativedelta


######################################## Date Input Widget
def date_value_input(df, date_col, operator, slot, allow_future=False):
    """
    Render the appropriate input widget for date filtering based on operator type.
    
    Args:
        df: DataFrame containing the date column
        date_col: Name of the date column to filter
        operator: Filter operator (Between, Window, or single date operators)
        slot: Streamlit container to render the widget in
        allow_future: Whether to allow future date windows
        
    Returns:
        The selected date value(s)
    """
    with slot:
        # ---- Between ----
        if operator == "Between":
            if not df[date_col].isna().all():
                min_date = pd.to_datetime(df[date_col].min(), errors="coerce")
                max_date = pd.to_datetime(df[date_col].max(), errors="coerce")
                default_range = (min_date.date(), max_date.date())
            else:
                default_range = (None, None)

            date_range = st.date_input(
                "Select date range",
                value=default_range,
                label_visibility="hidden",
                key=f"date_between_{date_col}",
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
                key=f"window_{date_col}",
                placeholder="Type 'last x days' or pick preset",
                help="You can type custom windows like 'last 2 quarters'.",
            )
            if val:
                val = [v.strip().lower() for v in val]
            return val

        # ---- Single Date ----
        else:
            if not df[date_col].isna().all():
                default_date = pd.to_datetime(df[date_col].max(), errors="coerce").date()
            else:
                default_date = None

            val = st.date_input(
                "Select date",
                value=default_date,
                label_visibility="hidden",
                key=f"date_single_{date_col}",
            )
            return val


######################################## Add Date Filter
def add_date_filter(date_col, operator, value, key):
    """
    Add a date filter to session state with validation.
    
    Args:
        date_col: Name of the date column
        operator: Filter operator
        value: Filter value(s)
        key: Unique key for this filter instance
    """
    key_name = f"date_filters_{key}"
    if key_name not in st.session_state:
        st.session_state[key_name] = []

    def parse_date(v):
        if isinstance(v, (list, tuple)):
            return [parse_date(x) for x in v]
        if isinstance(v, (pd.Timestamp, type(pd.Timestamp.now().date()))):
            return pd.to_datetime(v, errors="coerce")
        if isinstance(v, str):
            v = v.strip().replace("/", "-")
            return pd.to_datetime(v, errors="coerce")
        return v

    # ---------- Validation ----------
    if operator == "Between":
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            st.toast(f"Date filter ignored (invalid range)", icon="⚠️")
            return
        value = parse_date(value)
        if any(pd.isna(v) for v in value):
            st.toast(f"Date filter ignored (invalid date range)", icon="⚠️")
            return

    elif operator in ["=", "≥", "≤", "≠"]:
        if isinstance(value, (list, tuple)) and len(value) == 1:
            value = value[0]
        parsed = parse_date(value)
        if isinstance(parsed, pd.Timestamp) and not pd.isna(parsed):
            value = parsed
        else:
            st.toast(f"Date filter ignored (invalid date)", icon="⚠️")
            return

    elif operator == "Window":
        if not value or not isinstance(value, (list, tuple)):
            st.toast(f"Date filter ignored (invalid window)", icon="⚠️")
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
            st.toast(f"Date filter ignored (unrecognized window)", icon="⚠️")
            return

    st.session_state[key_name].append(
        {"column": date_col, "operator": operator, "value": value}
    )


######################################## Apply Date Filters
def apply_date_filters(df, date_col, key):
    """
    Apply all date filters to the DataFrame using AND logic.
    
    Args:
        df: DataFrame to filter
        date_col: Name of the date column to filter on
        key: Unique key for this filter instance
        
    Returns:
        Filtered DataFrame
    """
    key_name = f"date_filters_{key}"
    if key_name not in st.session_state or not st.session_state[key_name]:
        return df

    filtered_df = df.copy()

    # Ensure date column is datetime
    filtered_df[date_col] = pd.to_datetime(filtered_df[date_col], errors="coerce")
    filtered_df = filtered_df.loc[filtered_df[date_col].notna()]

    for f in st.session_state[key_name]:
        op_ = f["operator"]
        value = f["value"]

        try:
            # -------- BETWEEN --------
            if op_ == "Between" and isinstance(value, (tuple, list)) and len(value) == 2:
                v0, v1 = value
                v0 = pd.to_datetime(v0, errors="coerce")
                v1 = pd.to_datetime(v1, errors="coerce")
                filtered_df = filtered_df[
                    (filtered_df[date_col] >= v0) & (filtered_df[date_col] <= v1)
                ]

            # -------- COMPARISON OPERATORS --------
            elif op_ in ["=", "≥", "≤", "≠"]:
                value = pd.to_datetime(value, errors="coerce")
                
                if op_ == "=":
                    filtered_df = filtered_df[filtered_df[date_col] == value]
                elif op_ == "≥":
                    filtered_df = filtered_df[filtered_df[date_col] >= value]
                elif op_ == "≤":
                    filtered_df = filtered_df[filtered_df[date_col] <= value]
                elif op_ == "≠":
                    filtered_df = filtered_df[filtered_df[date_col] != value]

            # -------- WINDOW --------
            elif op_ == "Window":
                # Use dataset max as reference point
                dataset_max = pd.to_datetime(df[date_col], errors="coerce").max()
                if pd.isna(dataset_max):
                    continue
                now = dataset_max.normalize()

                mask = pd.Series(False, index=filtered_df.index)

                for v in value if isinstance(value, (list, tuple)) else [value]:
                    if not v:
                        continue
                    txt = str(v).lower().strip()
                    valid_window = False

                    # ---------- Explicit Keywords ----------
                    if txt == "today":
                        valid_window = True
                        cond = filtered_df[date_col].dt.normalize() == now
                    elif txt == "yesterday":
                        valid_window = True
                        cond = filtered_df[date_col].dt.normalize() == (now - pd.Timedelta(days=1))
                    elif txt == "this week":
                        valid_window = True
                        start = now - pd.Timedelta(days=now.weekday())
                        end = start + pd.Timedelta(days=6)
                        cond = filtered_df[date_col].between(start, end)
                    elif txt == "last week":
                        valid_window = True
                        start = now - pd.Timedelta(days=now.weekday() + 7)
                        end = start + pd.Timedelta(days=6)
                        cond = filtered_df[date_col].between(start, end)
                    elif txt == "next week":
                        valid_window = True
                        start = now + pd.Timedelta(days=7 - now.weekday())
                        end = start + pd.Timedelta(days=6)
                        cond = filtered_df[date_col].between(start, end)
                    elif txt == "this month":
                        valid_window = True
                        start = now.replace(day=1)
                        end = (start + pd.DateOffset(months=1)) - pd.Timedelta(days=1)
                        cond = filtered_df[date_col].between(start, end)
                    elif txt == "last month":
                        valid_window = True
                        start = (now.replace(day=1) - pd.DateOffset(months=1)).replace(day=1)
                        end = (start + pd.DateOffset(months=1)) - pd.Timedelta(days=1)
                        cond = filtered_df[date_col].between(start, end)
                    elif txt == "next month":
                        valid_window = True
                        start = (now.replace(day=1) + pd.DateOffset(months=1))
                        end = (start + pd.DateOffset(months=1)) - pd.Timedelta(days=1)
                        cond = filtered_df[date_col].between(start, end)
                    elif txt == "this quarter":
                        valid_window = True
                        q = (now.month - 1) // 3 + 1
                        start = pd.Timestamp(year=now.year, month=3 * (q - 1) + 1, day=1)
                        end = (start + pd.DateOffset(months=3)) - pd.Timedelta(days=1)
                        cond = filtered_df[date_col].between(start, end)
                    elif txt == "last quarter":
                        valid_window = True
                        q = (now.month - 1) // 3
                        year = now.year if q > 0 else now.year - 1
                        q = q if q > 0 else 4
                        start = pd.Timestamp(year=year, month=3 * (q - 1) + 1, day=1)
                        end = (start + pd.DateOffset(months=3)) - pd.Timedelta(days=1)
                        cond = filtered_df[date_col].between(start, end)
                    elif txt == "next quarter":
                        valid_window = True
                        q = (now.month - 1) // 3 + 2
                        year = now.year + (1 if q > 4 else 0)
                        q = ((q - 1) % 4) + 1
                        start = pd.Timestamp(year=year, month=3 * (q - 1) + 1, day=1)
                        end = (start + pd.DateOffset(months=3)) - pd.Timedelta(days=1)
                        cond = filtered_df[date_col].between(start, end)
                    elif txt == "this year":
                        valid_window = True
                        start = pd.Timestamp(year=now.year, month=1, day=1)
                        end = pd.Timestamp(year=now.year, month=12, day=31)
                        cond = filtered_df[date_col].between(start, end)
                    elif txt == "last year":
                        valid_window = True
                        y = now.year - 1
                        start = pd.Timestamp(year=y, month=1, day=1)
                        end = pd.Timestamp(year=y, month=12, day=31)
                        cond = filtered_df[date_col].between(start, end)
                    elif txt == "next year":
                        valid_window = True
                        y = now.year + 1
                        start = pd.Timestamp(year=y, month=1, day=1)
                        end = pd.Timestamp(year=y, month=12, day=31)
                        cond = filtered_df[date_col].between(start, end)

                    # ---------- Relative Patterns (last/next X days/weeks/etc) ----------
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
                        cond = filtered_df[date_col].between(min(start, end), max(start, end))

                    # ---------- Week Number (e.g., "week 23" or "week 23 2024") ----------
                    elif re.match(r"week\s+\d{1,2}(\s+\d{4})?", txt):
                        valid_window = True
                        m = re.match(r"week\s+(\d{1,2})(?:\s+(\d{4}))?", txt)
                        week_num, year = int(m.group(1)), int(m.group(2) or now.year)
                        start = pd.Timestamp.fromisocalendar(year, week_num, 1)
                        end = start + pd.Timedelta(days=6)
                        cond = filtered_df[date_col].between(start, end)

                    # ---------- Quarter (e.g., "q2" or "q2 2024") ----------
                    elif re.match(r"(q[1-4])(\s+\d{4})?", txt):
                        valid_window = True
                        m = re.match(r"q([1-4])(?:\s+(\d{4}))?", txt)
                        q, year = int(m.group(1)), int(m.group(2) or now.year)
                        start = pd.Timestamp(year=year, month=3 * (q - 1) + 1, day=1)
                        end = (start + pd.DateOffset(months=3)) - pd.Timedelta(days=1)
                        cond = filtered_df[date_col].between(start, end)

                    # ---------- Month Name (e.g., "January" or "Jan 2024") ----------
                    elif re.match(r"^[a-zA-Z]+(\s+\d{4})?$", txt, re.IGNORECASE):
                        valid_window = True
                        try:
                            parts = txt.strip().split()
                            month_name = parts[0].capitalize()
                            year = int(parts[1]) if len(parts) > 1 else now.year

                            # Try both full and abbreviated month formats
                            mnum = None
                            for fmt in ("%B", "%b"):
                                parsed = pd.to_datetime(month_name, format=fmt, errors="coerce")
                                if not pd.isna(parsed):
                                    mnum = parsed.month
                                    break

                            if mnum is not None:
                                start = pd.Timestamp(year=year, month=mnum, day=1)
                                end = (start + pd.DateOffset(months=1)) - pd.Timedelta(days=1)
                                cond = filtered_df[date_col].between(start, end)
                            else:
                                cond = pd.Series(False, index=filtered_df.index)
                        except Exception:
                            cond = pd.Series(False, index=filtered_df.index)

                    # ---------- Year (e.g., "2024") ----------
                    elif re.match(r"^\d{4}$", txt):
                        valid_window = True
                        y = int(txt)
                        start = pd.Timestamp(year=y, month=1, day=1)
                        end = pd.Timestamp(year=y, month=12, day=31)
                        cond = filtered_df[date_col].between(start, end)

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


######################################## Date Filter UI
def date_filter_ui(df, date_col, operators=None, allow_future=False, key="date_filter", layout="row"):
    """
    Create a date filter UI with operator and value selection wrapped in a form.
    
    Args:
        df: DataFrame to filter
        date_col: Name of the date column
        operators: List of operators to show (default: ["Between", "Window", "=", "≥", "≤", "≠"])
        allow_future: Whether to allow future date windows
        key: Unique key for this filter instance
        layout: "row" or "column" layout
        
    Returns:
        tuple: (filtered_df, filter_description_text)
    """
    key_name = f"date_filters_{key}"
    if key_name not in st.session_state:
        st.session_state[key_name] = []

    if operators is None:
        operators = ["Between", "Window", "=", "≥", "≤", "≠"]

    with st.form(key=f"{key}_form"):
        if layout == "row":
            operator_select, value_select = st.columns([1, 2])
            
            with operator_select:
                operator = st.selectbox(
                    "Date Operator",
                    operators,
                    key=f"{key}_op_row"
                )

            value = date_value_input(
                df, date_col, operator, value_select,
                allow_future=allow_future
            )
        else:
            operator = st.selectbox(
                "Date Operator",
                operators,
                key=f"{key}_op_col"
            )
            value = date_value_input(
                df, date_col, operator, st.container(),
                allow_future=allow_future
            )

        # Action buttons (form submit buttons)
        b1, b2 = st.columns(2)
        with b1:
            clear_clicked = st.form_submit_button("Clear All", use_container_width=True)
        with b2:
            commit_clicked = st.form_submit_button("Apply Filter", type="primary", use_container_width=True)

    # Handle form submissions
    if commit_clicked:
        add_date_filter(date_col, operator, value, key)
    if clear_clicked:
        st.session_state[key_name] = []

    # Apply filters and build description
    filtered_df = apply_date_filters(df, date_col, key)
    applied = [f"{f['operator']} {f['value']}" for f in st.session_state[key_name]]
    filter_text = " AND ".join(applied) if applied else "No date filters applied"
    
    return filtered_df, filter_text


######################################## Get Active Window
def get_active_window(key):
    """
    Get the currently active Window filter value.
    
    Args:
        key: Unique key for the filter instance
        
    Returns:
        str or None: The active window filter (e.g., 'this month', 'last 7 days') or None
    """
    filters = st.session_state.get(f"date_filters_{key}", [])
    for f in filters:
        if f["operator"] == "Window" and f["value"]:
            return f["value"][0].lower()
    return None


######################################## Clear All Filters
def clear_date_filters(key):
    """
    Programmatically clear all date filters for a given key.
    
    Args:
        key: Unique key for the filter instance
    """
    key_name = f"date_filters_{key}"
    if key_name in st.session_state:
        st.session_state[key_name] = []
