# ui/app.py

import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
from streamlit_autorefresh import st_autorefresh

# Ensure project root is importable (works even when Streamlit runs from ui/)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from storage.read_repository import JournalReadRepository  # type: ignore


LOCAL_TZ = ZoneInfo("America/New_York")


# ---------- Helpers ----------

def parse_iso(dt_str: str) -> datetime | None:
    if not dt_str:
        return None
    try:
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


def get_session_signature(repo: JournalReadRepository, session_id: int) -> tuple[int, int, int, int]:
    """
    Lightweight fingerprint of a session:
    (utterance_count, max_utter_id, action_count, max_action_id)

    We use this to detect if anything changed before reloading full lists.
    """
    cur = repo.conn.cursor()

    cur.execute(
        "SELECT COUNT(*) AS c, COALESCE(MAX(id), 0) AS m "
        "FROM utterances WHERE session_id = ?",
        (session_id,),
    )
    uc, um = cur.fetchone()

    cur.execute(
        "SELECT COUNT(*) AS c, COALESCE(MAX(id), 0) AS m "
        "FROM actions WHERE session_id = ?",
        (session_id,),
    )
    ac, am = cur.fetchone()

    return int(uc), int(um), int(ac), int(am)


# ---------- Streamlit App ----------

def main():
    st.set_page_config(page_title="Lab Voice Journal", layout="wide")
    st.title("🧪 Lab Voice Journal")

    # Auto-rerun the script every 500 ms without reloading the browser
    st_autorefresh(interval=500, key="journal_autorefresh")

    repo = JournalReadRepository()

    # --- Sidebar: sessions ---
    st.sidebar.header("Sessions")

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
    st.sidebar.caption("Live view updates ~2x/sec while recording.")

    # --- Efficient data loading with change detection ---

    # Compute current fingerprint of this session from DB
    signature = get_session_signature(repo, session.id)

    # Initialize session_state buckets
    if "journal_cache" not in st.session_state:
        st.session_state.journal_cache = {}

    cache = st.session_state.journal_cache.get(session.id)

    if cache and cache.get("signature") == signature:
        # Nothing changed – reuse cached utterances/actions
        utterances = cache["utterances"]
        actions = cache["actions"]
    else:
        # Something changed (or first load) – fetch fresh data
        utterances = repo.get_utterances(session.id)
        actions = repo.get_actions(session.id)
        st.session_state.journal_cache[session.id] = {
            "signature": signature,
            "utterances": utterances,
            "actions": actions,
        }

    # --- Main layout ---
    col_transcript, col_actions = st.columns([3, 1])

    # Transcript column
    with col_transcript:
        st.subheader("Transcript")

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

                # Group by minute with a small header
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
