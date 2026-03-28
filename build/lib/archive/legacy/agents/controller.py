# agents/controller.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import logging
import os
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Protocol, cast

from .db import SessionLocal, init_db
from .models import Session, Utterance
from sqlalchemy import or_
from stt.context import ContextProcessor
from stt.trigger import TriggerEvaluator

# ------- Logger -------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("labj")

# Load STTClient from stt/STT-module/stt.py without shadowing the stt package.
_STT_MODULE_PATH = (
    Path(__file__).resolve().parent.parent / "stt" / "STT-module" / "stt.py"
)
_STT_SPEC = spec_from_file_location("stt_module_client", _STT_MODULE_PATH)
if _STT_SPEC is None or _STT_SPEC.loader is None:
    raise ImportError(f"Cannot load STT module from {_STT_MODULE_PATH}")
_stt_module = module_from_spec(_STT_SPEC)
_STT_SPEC.loader.exec_module(_stt_module)
STTClient = _stt_module.STTClient


class STTClientLike(Protocol):
    def start(self) -> None: ...

    def stop(self) -> str: ...


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

# ---------- Sub-windows cache ----------
SubWindowData = Dict[str, Any]
SUBWINDOW_CACHE: Dict[str, SubWindowData] = {}  # key = window_id (str)
SUBWINDOW_COUNTER = 0

# ---------- STT globals ----------
# Track listening + whether we should append text while still listening.
STT_STATE = {"listening": True, "transcribing": True}
# Track current STT target session
CURRENT_SESSION_ID: Optional[int] = None
# STT client instance (initialized on startup)
stt_client: Optional[STTClientLike] = None
# Context processor for MCP command extraction
context_processor: Optional[ContextProcessor] = None
# Keyword trigger fallback when LLM tool-calling does not return commands
trigger_evaluator = TriggerEvaluator()


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

    # always append to the "last" session for now #TODO - good prints
    # last_sid = sorted(SESSION_CACHE.keys())[-1]
    # SESSION_CACHE[last_sid]["blocks"].append(
    #     {
    #         "id": f"log-{datetime.utcnow().timestamp()}",
    #         "type": "log",
    #         "content": {"text": f"[log] {message}"},
    #     }
    # )


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
                "isArchived": bool(s.ended_at),
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


def append_utterance_in_db(
    session_id: int, text: str, source: str = "manual", metadata: Optional[str] = None
) -> Utterance:
    """
    Insert a new utterance row for the given session.

    Args:
        session_id: ID of the session
        text: Utterance text (enhanced text if processed by LLM)
        source: Source of utterance ("stt", "manual", "calculator", etc.)
        metadata: Optional JSON string with raw_text, intent, LLM processing info
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
            metadata_json=metadata,
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
    global SESSION_CACHE, CURRENT_SESSION_ID

    if CURRENT_SESSION_ID and CURRENT_SESSION_ID in SESSION_CACHE:
        return CURRENT_SESSION_ID

    db = SessionLocal()
    try:
        last_db_session = db.query(Session).order_by(Session.id.desc()).first()
    finally:
        db.close()

    if not SESSION_CACHE and last_db_session:
        load_cache_from_db()

    if CURRENT_SESSION_ID and CURRENT_SESSION_ID in SESSION_CACHE:
        return CURRENT_SESSION_ID

    if last_db_session and last_db_session.id in SESSION_CACHE:
        CURRENT_SESSION_ID = last_db_session.id
        return last_db_session.id

    if SESSION_CACHE:
        CURRENT_SESSION_ID = sorted(SESSION_CACHE.keys())[-1]
        return CURRENT_SESSION_ID

    # Create fresh live session
    title = "Live Lab Session"
    session_id = create_session_in_db(title)
    SESSION_CACHE[session_id] = {
        "id": session_id,
        "title": title,
        "description": "",
        "isFavorite": False,
        "isArchived": False,
        "blocks": [],
    }
    add_log_block(f"Created live session for STT: {session_id}")
    CURRENT_SESSION_ID = session_id
    return session_id


def handle_stt_text(enhanced_text: str, context_result: Dict[str, Any]):
    """
    Called by STT worker whenever a chunk of text is ready.
    Writes enhanced text to DB + updates RAM cache + adds log block.
    Preserves raw transcription in metadata.

    Args:
        enhanced_text: LLM-enhanced text (grammar corrected, filler removed)
        context_result: Full context processing result with raw_text, intent, etc.
    """
    enhanced_text = enhanced_text.strip()
    if not enhanced_text:
        return

    session_id = ensure_live_session_id()

    # Build metadata JSON with raw text and processing info
    metadata = {
        "raw_text": context_result.get("raw_text", enhanced_text),
        "intent": context_result.get("intent", "journal"),
        "processed": context_result.get("metadata", {}).get("processed", False),
        "model": context_result.get("metadata", {}).get("model", "none"),
        "timestamp": context_result.get("metadata", {}).get("timestamp", now_iso()),
    }

    u = append_utterance_in_db(
        session_id, enhanced_text, source="stt", metadata=json.dumps(metadata)
    )

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
    add_log_block(
        f"STT → session {session_id}: {enhanced_text[:80] + '…' if len(enhanced_text) > 80 else enhanced_text}"
    )
    logger.info(
        "STT text appended to session_id=%s utterance_id=%s (raw=%s)",
        session_id,
        u.id,
        context_result.get("raw_text", "")[:50],
    )


def handle_stt_commands(commands: List[Dict[str, Any]]) -> None:
    """
    Execute MCP tool calls extracted by LLM context processor.

    Args:
        commands: List of command dicts with 'name' and 'arguments'
    """
    global STT_STATE, CURRENT_SESSION_ID, SUBWINDOW_CACHE, SUBWINDOW_COUNTER, stt_client

    for cmd in commands:
        name = cmd.get("name", "")
        args = cmd.get("arguments", {})

        if name == "pause_transcription":
            STT_STATE["transcribing"] = False
            add_log_block("LLM command: pause transcription")
            logger.info("Transcription paused by LLM command")

        elif name == "resume_transcription":
            STT_STATE["transcribing"] = True
            add_log_block("LLM command: resume transcription")
            logger.info("Transcription resumed by LLM command")

        elif name == "stop_listening":
            STT_STATE["listening"] = False
            add_log_block("LLM command: stop listening")
            logger.info("Stop listening triggered by LLM – shutting down STT client")
            if stt_client:
                try:
                    stt_client.stop()
                except Exception:
                    logger.exception("Error stopping STT client after stop_listening")

        elif name == "new_session":
            title = args.get("title", "").strip() or f"Live Session {now_iso()}"
            session_id = create_session_in_db(title)
            SESSION_CACHE[session_id] = {
                "id": session_id,
                "title": title,
                "description": "",
                "isFavorite": False,
                "isArchived": False,
                "blocks": [],
            }
            CURRENT_SESSION_ID = session_id
            add_log_block(f"LLM command: started new session {session_id} - {title}")
            logger.info("New session created by LLM id=%s title=%s", session_id, title)

        elif name == "create_note":
            SUBWINDOW_COUNTER += 1
            window_id = f"note-{SUBWINDOW_COUNTER}"
            initial_content = args.get("initial_content", "")
            SUBWINDOW_CACHE[window_id] = {
                "id": window_id,
                "type": "note",
                "title": f"Note {SUBWINDOW_COUNTER}",
                "content": initial_content,
                "position": {
                    "x": 100 + (SUBWINDOW_COUNTER * 30),
                    "y": 100 + (SUBWINDOW_COUNTER * 30),
                },
                "size": {"width": 300, "height": 200},
            }
            add_log_block(f"LLM command: created note window {window_id}")
            logger.info("Note window created by LLM id=%s", window_id)

        elif name == "create_calculator":
            SUBWINDOW_COUNTER += 1
            window_id = f"calc-{SUBWINDOW_COUNTER}"

            # Extract initial expression from LLM args
            initial_expr = args.get("initial_expression", "")
            initial_state = {"currentExpression": initial_expr, "history": []}

            SUBWINDOW_CACHE[window_id] = {
                "id": window_id,
                "type": "calculator",
                "title": f"Calculator {SUBWINDOW_COUNTER}",
                "content": json.dumps(initial_state),
                "position": {
                    "x": 150 + (SUBWINDOW_COUNTER * 30),
                    "y": 150 + (SUBWINDOW_COUNTER * 30),
                },
                "size": {"width": 400, "height": 500},
            }
            add_log_block(
                f"LLM command: created calculator window {window_id} with expr={initial_expr!r}"
            )
            logger.info(
                "Calculator window created by LLM id=%s expr=%s",
                window_id,
                initial_expr,
            )


def on_transcription_callback(text: str) -> None:
    """
    Callback fired by STTClient after each pause in speech.
    Processes the raw transcription through ContextProcessor for MCP commands
    and journal text enhancement.
    """
    global context_processor

    if not text or not text.strip():
        return

    raw_text = text.strip()
    logger.info("STT received: %s", raw_text[:80])

    # Process through ContextProcessor for intent detection and command extraction
    if context_processor:
        context_result = context_processor.process(raw_text)
    else:
        # Fallback if context processor not initialized
        context_result = {
            "enhanced_text": raw_text,
            "raw_text": raw_text,
            "commands": [],
            "intent": "journal",
            "metadata": {"processed": False},
        }

    # Fallback to deterministic keyword triggers if LLM returned no commands
    commands = context_result.get("commands", [])
    if not commands:
        fallback_action = trigger_evaluator.evaluate(raw_text)
        if fallback_action:
            commands = [{"name": fallback_action, "arguments": {}}]
            logger.info("Fallback trigger command: %s", fallback_action)

    # Handle any extracted MCP commands
    if commands:
        handle_stt_commands(commands)

    # Handle journal text if transcribing is enabled
    enhanced_text = context_result.get("enhanced_text", "")
    if enhanced_text and STT_STATE["transcribing"]:
        handle_stt_text(enhanced_text, context_result)


logger.info("Startup: SESSION_CACHE size = %d", len(SESSION_CACHE))
add_log_block(f"Startup: cache has {len(SESSION_CACHE)} sessions")


def start_stt_client():
    """
    Initialize and start the STT client with the new STT module.
    """
    global stt_client, context_processor, STT_STATE

    if stt_client is not None:
        logger.info("STT client already initialized")
        return

    # Initialize context processor for MCP command extraction
    context_processor = ContextProcessor(enabled=True)

    # Create and start STT client
    stt_api_url = os.getenv("STT_API_URL", "http://localhost:8001/transcribe")
    stt_client = cast(
        STTClientLike,
        STTClient(
            on_transcription=on_transcription_callback,
            language="en",
            api_url=stt_api_url,
        ),
    )
    stt_client.start()
    STT_STATE["listening"] = True
    STT_STATE["transcribing"] = True
    logger.info("STT client started (api_url=%s)", stt_api_url)


@app.on_event("startup")
def on_startup():
    # DB/cache already initialized at import; you can keep or move them here if you prefer.
    start_stt_client()
    add_log_block("on_startup: STT client initialized")


# ---------- API models ----------
class CommandRequest(BaseModel):
    text: str


class UpdateSessionTitleRequest(BaseModel):
    title: str


class CreateSessionRequest(BaseModel):
    title: Optional[str] = None


class ArchiveSessionRequest(BaseModel):
    archived: bool = True


class UpdateSubWindowRequest(BaseModel):
    content: Optional[str] = None
    position: Optional[Dict[str, int]] = None
    size: Optional[Dict[str, int]] = None


class CloseSubWindowRequest(BaseModel):
    window_id: str


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
            "isArchived": s.get("isArchived", False),
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
            "isArchived": s.get("isArchived", False),
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


@app.post("/sessions")
def create_session(req: CreateSessionRequest):
    """
    Create a new session with an optional title.
    """
    title = (req.title or "").strip() or "New Session"
    session_id = create_session_in_db(title)
    SESSION_CACHE[session_id] = {
        "id": session_id,
        "title": title,
        "description": "",
        "isFavorite": False,
        "isArchived": False,
        "blocks": [],
    }
    add_log_block(f"Session created via API: {session_id} ({title})")
    logger.info("Session created via API id=%s title=%s", session_id, title)
    return {"status": "ok", "session_id": session_id, "title": title}


@app.post("/sessions/{session_id}/archive")
def archive_session(session_id: int, req: ArchiveSessionRequest):
    """
    Mark a session archived (sets ended_at). Can also unarchive if archived=False.
    """
    db = SessionLocal()
    try:
        s = db.query(Session).filter(Session.id == session_id).first()
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")

        s.ended_at = now_iso() if req.archived else None
        db.commit()

        if session_id in SESSION_CACHE:
            SESSION_CACHE[session_id]["isArchived"] = bool(s.ended_at)

        action = "archived" if s.ended_at else "unarchived"
        add_log_block(f"Session {session_id} {action}")
        logger.info("Session %s %s", session_id, action)
        return {"status": "ok", "session_id": session_id, "archived": bool(s.ended_at)}
    finally:
        db.close()


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
        subq = (
            db.query(Utterance.session_id)
            .filter(Utterance.text.ilike(pattern))
            .subquery()
        )
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


# ---------- Sub-window endpoints ----------


@app.get("/subwindows")
def list_subwindows():
    """
    Get all active sub-windows.
    """
    return list(SUBWINDOW_CACHE.values())


@app.post("/subwindows/{window_id}")
def update_subwindow(window_id: str, req: UpdateSubWindowRequest):
    """
    Update a sub-window's content, position, or size.
    """
    if window_id not in SUBWINDOW_CACHE:
        raise HTTPException(status_code=404, detail="Sub-window not found")

    window = SUBWINDOW_CACHE[window_id]

    if req.content is not None:
        window["content"] = req.content
    if req.position is not None:
        window["position"] = req.position
    if req.size is not None:
        window["size"] = req.size

    logger.info("Sub-window %s updated", window_id)
    return {"status": "ok", "window": window}


@app.delete("/subwindows/{window_id}")
def close_subwindow(window_id: str):
    """
    Close/delete a sub-window.
    """
    if window_id not in SUBWINDOW_CACHE:
        raise HTTPException(status_code=404, detail="Sub-window not found")

    del SUBWINDOW_CACHE[window_id]
    add_log_block(f"Sub-window {window_id} closed")
    logger.info("Sub-window %s closed", window_id)
    return {"status": "ok", "window_id": window_id}
