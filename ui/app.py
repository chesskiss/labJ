# ui/app.py

import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

# Ensure project root is importable (works even when Streamlit runs from ui/)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from storage.read_repository import JournalReadRepository  # type: ignore


# You can later make this dynamic based on user preference
LOCAL_TZ = ZoneInfo("America/New_York")


# ---------- Helpers ----------

def parse_iso(dt_str: str) -> datetime | None:
    if not dt_str:
        return None
    try:
        # DB stores strings like "2025-11-15T06:59:50.811997Z"
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str)
    except Exception:
        return None


def format_dt_local(dt_str: str) -> str:
    dt = parse_iso(dt_str)
    if not dt:
        return ""
    return dt.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")


# ---------- Streamlit App ----------

def main():
    st.set_page_config(page_title="Lab Voice Journal", layout="wide")
    st.title("🧪 Lab Voice Journal")

    # --- Auto-refresh controls ---
    st.sidebar.header("Live view")
    refresh_interval = st.sidebar.slider(
        "Auto-refresh every (seconds)", min_value=0, max_value=10, value=3
    )
    if refresh_interval > 0:
        # Simple HTML meta refresh – reloads the page every N seconds
        st.markdown(
            f"""
            <meta http-equiv="refresh" content="{refresh_interval}">
            """,
            unsafe_allow_html=True,
        )

    # --- Sessions sidebar ---
    st.sidebar.header("Sessions")

    repo = JournalReadRepository()
    sessions = repo.list_sessions()
    if not sessions:
        st.sidebar.info("No sessions found yet.")
        st.write("Start the voice agent and record a session to see it here.")
        return

    session_labels = [
        f"#{s.id} – {format_dt_local(s.started_at)}"
        + (f" – {s.title}" if s.title else "")
        for s in sessions
    ]
    session_id_by_label = {label: s.id for label, s in zip(session_labels, sessions)}

    selected_label = st.sidebar.selectbox("Select session", session_labels)
    selected_session_id = session_id_by_label[selected_label]
    session = repo.get_session(selected_session_id)

    st.sidebar.markdown("---")
    st.sidebar.write(f"**Session ID:** {session.id}")
    st.sidebar.write(f"**Started:** {format_dt_local(session.started_at)}")
    if session.ended_at:
        st.sidebar.write(f"**Ended:** {format_dt_local(session.ended_at)}")
    else:
        st.sidebar.write("**Ended:** (ongoing)")

    # --- Main layout ---
    col_transcript, col_actions = st.columns([3, 1])

    # Transcript column
    with col_transcript:
        st.subheader("Transcript")

        utterances = repo.get_utterances(session.id)
        if not utterances:
            st.info("No utterances recorded for this session yet.")
        else:
            last_minute_bucket = None
            for utt in utterances:
                start_local_dt = parse_iso(utt.start_time)
                if start_local_dt:
                    local_time_str = start_local_dt.astimezone(LOCAL_TZ).strftime(
                        "%H:%M:%S"
                    )
                    minute_bucket = start_local_dt.replace(
                        second=0, microsecond=0
                    ).strftime("%H:%M")
                else:
                    local_time_str = ""
                    minute_bucket = None

                # Optional: group by minute (visual section headers)
                if minute_bucket and minute_bucket != last_minute_bucket:
                    st.markdown(f"#### 🕒 {minute_bucket}")
                    last_minute_bucket = minute_bucket

                st.markdown(
                    f"**[{local_time_str}]**  \n"
                    f"{utt.text}"
                )
                st.markdown("---")

    # Actions column
    with col_actions:
        st.subheader("Actions")

        actions = repo.get_actions(session.id)
        if not actions:
            st.write("No actions recorded.")
        else:
            for act in actions:
                time_str = format_dt_local(act.time)
                st.markdown(
                    f"**{time_str}**  \n"
                    f"`{act.action_type}`  \n"
                    f"{act.raw_text or ''}"
                )
                st.markdown("---")


if __name__ == "__main__":
    main()
