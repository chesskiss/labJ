from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
from stt.transcriber import Transcriber

app = FastAPI()
transcriber = Transcriber()  # your existing class

# In-memory store for now
SESSIONS: Dict[str, Dict[str, Any]] = {}

class CommandRequest(BaseModel):
    text: str

@app.get("/sessions")
def list_sessions():
    return [
        {
            "id": sid,
            "title": s.get("title", f"Session {sid}"),
            "description": s.get("description", ""),
            "isFavorite": s.get("isFavorite", False),
        }
        for sid, s in SESSIONS.items()
    ]

@app.get("/notebook")
def get_notebook():
    # flatten sessions for UI
    return [
        {
            "id": sid,
            "title": s.get("title", f"Session {sid}"),
            "blocks": s.get("blocks", []),
        }
        for sid, s in SESSIONS.items()
    ]

@app.post("/commands")
def handle_command(req: CommandRequest):
    """
    Central entry point for the bottom-right command console.
    Example commands:
    - "new session pcr run"
    - "new section results"
    - "note sample A at 37 degrees"
    """
    text = req.text.strip()
    # TODO: plug in your LLM or rule parser here
    result = parse_and_apply_command(text)
    return {"status": "ok", "applied": result}


def parse_and_apply_command(text: str) -> Dict[str, Any]:
    """
    Extremely simple parser; you can replace with LLM later.
    """
    lower = text.lower()
    global SESSIONS

    if lower.startswith("new session"):
        title = text.split("new session", 1)[1].strip(" :")
        sid = f"s{len(SESSIONS)+1}"
        SESSIONS[sid] = {
            "title": title or f"Session {sid}",
            "blocks": [],
            "isFavorite": False,
        }
        return {"type": "NEW_SESSION", "session_id": sid, "title": title}

    # Add more patterns here: "new section", "note", etc.
    # Or send to an LLM for structure.

    # Default: append as plain note to last session
    if SESSIONS:
        last_sid = list(SESSIONS.keys())[-1]
        SESSIONS[last_sid]["blocks"].append(
            {
                "id": f"b{len(SESSIONS[last_sid]['blocks'])+1}",
                "type": "paragraph",
                "content": {"text": text},
            }
        )
        return {"type": "APPEND_NOTE", "session_id": last_sid}

    # if no session exists, create one implicitly
    sid = "s1"
    SESSIONS[sid] = {
        "title": "Session 1",
        "blocks": [
            {"id": "b1", "type": "paragraph", "content": {"text": text}}
        ],
        "isFavorite": False,
    }
    return {"type": "CREATE_DEFAULT_SESSION", "session_id": sid}


# You can also add endpoints for STT audio uploads later:
# @app.post("/audio_chunk")
# def handle_audio_chunk(...):
#     text = transcriber.transcribe(...)
#     # then route text via parse_and_apply_command or straight into notebook


# To run:
#   uvicorn controller:app --reload
