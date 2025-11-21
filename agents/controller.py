# agents/controller.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging

from .db import SessionLocal, init_db
from .models import Session, Utterance, Action
from sqlalchemy import or_

# ------- Logger -------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("labj")

import threading
from stt.transcriber import Transcriber
from audio.mic_stream import MicrophoneStream

from env_config import (
    STT_SAMPLE_RATE,
    STT_MODEL_SIZE,
    CHUNK_SIZE,
)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


# ---------- RAM cache ----------
SessionData = Dict[str, Any]
SESSION_CACHE: Dict[int, SessionData] = {}  # key = session_id (int)

# ---------- STT globals ----------
transcriber = Transcriber(model_size=STT_MODEL_SIZE, compute_type="int8")
STT_THREAD_STARTED = False
# Track listening + whether we should append text while still listening.
STT_STATE = {"listening": True, "transcribing": True}


def now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def add_log_block(message: str):
    """
    Special block type we insert into SESSION_CACHE for debugging.
    Does NOT get written to utterances table (temporary feature).
    """
    # If no session exists yet, create a temporary one.
    if not SESSION_CACHE:
        sid = -1  # a pseudo-session for debug logs
        SESSION_CACHE[sid] = {
            "id": sid,
            "title": "Debug Log",
            "description": "",
            "isFavorite": False,
            "blocks": [],
        }

    # always append to the "last" session for now
    last_sid = sorted(SESSION_CACHE.keys())[-1]
    SESSION_CACHE[last_sid]["blocks"].append(
        {
            "id": f"log-{datetime.utcnow().timestamp()}",
            "type": "paragraph",
            "content": {"text": f"[log] {message}"},
        }
    )


def load_cache_from_db() -> None:
    """
    Load all sessions + their utterances from SQLite into RAM cache.
    """
    global SESSION_CACHE
    SESSION_CACHE.clear()
    db = SessionLocal()
    try:
        sessions = db.query(Session).order_by(Session.id).all()
        for s in sessions:
            # load utterances for each session, ordered by sequence_index
            utts = (
                db.query(Utterance)
                .filter(Utterance.session_id == s.id)
                .order_by(Utterance.sequence_index)
                .all()
            )
            blocks = []
            for u in utts:
                blocks.append(
                    {
                        "id": f"utt-{u.id}",
                        "type": "paragraph",
                        "content": {
                            "text": u.text,
                            "source": u.source,
                            "start_time": u.start_time,
                            "end_time": u.end_time,
                        },
                    }
                )

            SESSION_CACHE[s.id] = {
                "id": s.id,
                "title": s.title or f"Session {s.id}",
                "description": "",  # you can derive from metadata or first utterance later
                "isFavorite": False,  # store this in metadata if you want
                "blocks": blocks,
            }
    finally:
        db.close()


def create_session_in_db(title: str) -> int:
    """
    Insert a new session into SQLite and return its id.
    """
    db = SessionLocal()
    try:
        s = Session(
            started_at=now_iso(),
            ended_at=None,
            title=title,
            metadata=None,
            created_at=now_iso(),
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        return s.id
    finally:
        db.close()


def append_utterance_in_db(session_id: int, text: str, source: str = "manual") -> Utterance:
    """
    Insert a new utterance row for the given session.
    """
    db = SessionLocal()
    try:
        # find max sequence_index for this session
        max_idx = (
            db.query(Utterance.sequence_index)
            .filter(Utterance.session_id == session_id)
            .order_by(Utterance.sequence_index.desc())
            .first()
        )
        next_idx = (max_idx[0] + 1) if max_idx else 0

        t = now_iso()
        u = Utterance(
            session_id=session_id,
            start_time=t,
            end_time=t,
            sequence_index=next_idx,
            text=text,
            source=source,
            created_at=t,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        return u
    finally:
        db.close()


# Populate cache from DB at startup
load_cache_from_db()


def ensure_live_session_id() -> int:
    """
    Returns an existing session id to append STT to,
    or creates one if none exist.
    """
    global SESSION_CACHE
    if SESSION_CACHE:
        # append to the last session by id
        return sorted(SESSION_CACHE.keys())[-1]

    title = "Live Lab Session"
    session_id = create_session_in_db(title)
    SESSION_CACHE[session_id] = {
        "id": session_id,
        "title": title,
        "description": "",
        "isFavorite": False,
        "blocks": [],
    }
    add_log_block(f"Created live session for STT: {session_id}")
    return session_id

def handle_stt_text(text: str):
    """
    Called by STT worker whenever a chunk of text is ready.
    Writes to DB + updates RAM cache + adds log block.
    """
    text = text.strip()
    if not text:
        return

    session_id = ensure_live_session_id()
    u = append_utterance_in_db(session_id, text, source="stt")

    blocks = SESSION_CACHE[session_id].setdefault("blocks", [])
    blocks.append(
        {
            "id": f"utt-{u.id}",
            "type": "paragraph",
            "content": {
                "text": u.text,
                "source": u.source,
                "start_time": u.start_time,
                "end_time": u.end_time,
            },
        }
    )
    add_log_block(f"STT → session {session_id}: {text[:80] + '…' if len(text) > 80 else text}")
    logger.info("STT text appended to session_id=%s utterance_id=%s", session_id, u.id)


def handle_stt_action(action: str, stream: Optional[MicrophoneStream] = None) -> None:
    """
    React to control phrases detected by the Transcriber.
    """
    global STT_STATE

    if action == "pause_transcription":
        STT_STATE["transcribing"] = False
        add_log_block("STT command: pause transcription")
        logger.info("STT paused by voice command")
    elif action == "resume_transcription":
        STT_STATE["transcribing"] = True
        add_log_block("STT command: resume transcription")
        logger.info("STT resumed by voice command")
    elif action == "stop_listening":
        STT_STATE["listening"] = False
        add_log_block("STT command: stop listening")
        logger.info("STT stop_listening triggered – shutting down mic stream")
        if stream:
            try:
                stream.stop()
            except Exception:
                logger.exception("Error stopping microphone stream after stop_listening")

def stt_worker():
    """
    Blocking STT loop running in a background thread.
    Listens to microphone and calls handle_stt_text(text) for each chunk.
    """
    add_log_block("STT worker started")
    logger.info("STT worker started")

    while STT_STATE["listening"]:
        try:
            with MicrophoneStream(sample_rate=STT_SAMPLE_RATE, chunk_size=CHUNK_SIZE) as stream:
                while STT_STATE["listening"] and stream.is_streaming:
                    chunk = stream.get_audio_chunk(timeout=0.5)
                    if chunk is None:
                        continue

                    text, action = transcriber.transcribe(chunk, sample_rate=STT_SAMPLE_RATE)

                    if action:
                        handle_stt_action(action, stream)
                        if not STT_STATE["listening"]:
                            break

                    if text and STT_STATE["transcribing"]:
                        handle_stt_text(text)
        except Exception as e:
            logger.exception("STT worker error: %s", e)
            add_log_block(f"STT worker error: {e!r}")
            # small backoff to avoid tight crash loop
            import time
            time.sleep(2.0)



logger.info("Startup: SESSION_CACHE size = %d", len(SESSION_CACHE))
add_log_block(f"Startup: cache has {len(SESSION_CACHE)} sessions")


def start_stt_thread_once():
    global STT_THREAD_STARTED
    if STT_THREAD_STARTED:
        return
    STT_THREAD_STARTED = True
    t = threading.Thread(target=stt_worker, daemon=True)
    t.start()
    logger.info("STT background thread started")


@app.on_event("startup")
def on_startup():
    # DB/cache already initialized at import; you can keep or move them here if you prefer.
    start_stt_thread_once()
    add_log_block("on_startup: STT thread initialized")



# ---------- API models ----------
class CommandRequest(BaseModel):
    text: str

class UpdateSessionTitleRequest(BaseModel):
    title: str


# ---------- API endpoints ----------
@app.get("/sessions")
def list_sessions():
    """
    Sidebar data: id, title, description, isFavorite.
    Driven by RAM cache synced from SQLite.
    """
    return [
        {
            "id": sid,
            "title": s["title"],
            "description": s.get("description", ""),
            "isFavorite": s.get("isFavorite", False),
        }
        for sid, s in sorted(SESSION_CACHE.items())
    ]


@app.get("/notebook")
def get_notebook():
    """
    Notebook view: all sessions + their blocks.
    """
    return [
        {
            "id": sid,
            "title": s["title"],
            "blocks": s.get("blocks", []),
        }
        for sid, s in sorted(SESSION_CACHE.items())
    ]


@app.post("/commands")
def handle_command(req: CommandRequest):
    """
    Bottom-right console.
    Very simple command handling:
      - "new session XYZ" -> create a session
      - anything else     -> append note to last session (or create one)
    """
    text = req.text.strip()
    result = parse_and_apply_command(text)
    return {"status": "ok", "applied": result}


@app.put("/sessions/{session_id}/title")
def update_session_title(session_id: int, req: UpdateSessionTitleRequest):
    """
    Rename a session; updates DB and RAM cache.
    """
    db = SessionLocal()
    try:
        s = db.query(Session).filter(Session.id == session_id).first()
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        s.title = req.title.strip() or f"Session {session_id}"
        db.commit()

        if session_id in SESSION_CACHE:
            SESSION_CACHE[session_id]["title"] = s.title

        add_log_block(f"Session {session_id} renamed to {s.title!r}")
        logger.info("Session %s renamed to %s", session_id, s.title)
        return {"status": "ok", "session_id": session_id, "title": s.title}
    finally:
        db.close()


# ---------- Search ----------


@app.get("/search")
def search_sessions(q: str):
    """
    Search across session titles/metadata and utterance text.
    Returns the same shape as /sessions so the UI can reuse it.
    """
    query = q.strip()
    if not query:
        logger.info("GET /search (empty) -> returning /sessions")
        add_log_block("GET /search: empty query → /sessions")
        return list_sessions()

    db = SessionLocal()
    pattern = f"%{query}%"
    try:
        subq = db.query(Utterance.session_id).filter(Utterance.text.ilike(pattern)).subquery()
        rows = (
            db.query(Session)
            .filter(
                or_(
                    Session.title.ilike(pattern),
                    Session.metadata_json.ilike(pattern),
                    Session.id.in_(subq),
                )
            )
            .order_by(Session.id)
            .all()
        )

        results = [
            {
                "id": s.id,
                "title": s.title or f"Session {s.id}",
                "description": "",
                "isFavorite": False,
            }
            for s in rows
        ]

        add_log_block(f"GET /search q={query!r}: {len(results)} hits")
        logger.info("GET /search q=%s -> %d sessions", query, len(results))
        return results
    finally:
        db.close()


# ---------- Command parsing ----------


def parse_and_apply_command(text: str) -> Dict[str, Any]:
    global SESSION_CACHE
    lower = text.lower()

    # NEW SESSION
    if lower.startswith("new session"):
        title = text.split("new session", 1)[1].strip(" :")
        title = title or "Untitled session"
        session_id = create_session_in_db(title)

        SESSION_CACHE[session_id] = {
            "id": session_id,
            "title": title,
            "description": "",
            "isFavorite": False,
            "blocks": [],
        }
        return {"type": "NEW_SESSION", "session_id": session_id, "title": title}

    # APPEND NOTE to last session
    if SESSION_CACHE:
        last_session_id = sorted(SESSION_CACHE.keys())[-1]
        u = append_utterance_in_db(last_session_id, text, source="manual")

        blocks = SESSION_CACHE[last_session_id].setdefault("blocks", [])
        blocks.append(
            {
                "id": f"utt-{u.id}",
                "type": "paragraph",
                "content": {
                    "text": u.text,
                    "source": u.source,
                    "start_time": u.start_time,
                    "end_time": u.end_time,
                },
            }
        )
        return {"type": "APPEND_NOTE", "session_id": last_session_id}

    # No sessions yet: create one implicitly and add note
    title = "Session 1"
    session_id = create_session_in_db(title)
    SESSION_CACHE[session_id] = {
        "id": session_id,
        "title": title,
        "description": "",
        "isFavorite": False,
        "blocks": [],
    }
    u = append_utterance_in_db(session_id, text, source="manual")
    SESSION_CACHE[session_id]["blocks"].append(
        {
            "id": f"utt-{u.id}",
            "type": "paragraph",
            "content": {
                "text": u.text,
                "source": u.source,
                "start_time": u.start_time,
                "end_time": u.end_time,
            },
        }
    )
    return {"type": "CREATE_DEFAULT_SESSION", "session_id": session_id}
