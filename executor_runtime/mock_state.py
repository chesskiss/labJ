"""In-memory runtime state used by executor mock tools."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MockRuntime:
    """Mutable in-memory runtime state for execution tests and local runs."""

    active_session_exists: bool = True
    active_session_id: uuid.UUID | None = None
    calculator_slots: dict[int, dict[str, Any]] = field(default_factory=dict)
    journal_entries: list[str] = field(default_factory=list)
    protocol_index: dict[str, dict[str, Any]] = field(default_factory=dict)
    observations: list[str] = field(default_factory=list)
    journal_write_tool: Any | None = None
    note_capture_title: str | None = None
    note_capture_metadata: dict[str, Any] = field(default_factory=dict)
    mic_draft_active: bool = False
    mic_draft_base_content: str | None = None
    mic_draft_base_initialized: bool = False
