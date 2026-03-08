"""Pydantic schemas defining the stable in-memory runtime state contract."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CalculatorSlotValue(BaseModel):
    """Value container for a calculator slot."""

    value: float
    unit: str | None = None


class JournalEntry(BaseModel):
    """In-memory journal entry representation."""

    entry_index: int
    content: str
    created_by: str = "mock_tool"
    sequence: int = 0


class ProtocolRecord(BaseModel):
    """Mock protocol index record."""

    title: str
    content: str


class ObservationRecord(BaseModel):
    """Captured observation entry for runtime simulation."""

    observation_index: int
    content: str
    created_by: str = "mock_tool"
    sequence: int = 0


class RecentResult(BaseModel):
    """Compact recent result used in future session summaries."""

    label: str
    value: float | int | str
    unit: str | None = None


class MockRuntimeState(BaseModel):
    """Top-level mock runtime state shared by executor + mock tools."""

    active_session_exists: bool = False
    active_session_id: str | None = None
    active_session_title: str | None = None
    calculator_slots: dict[int, CalculatorSlotValue] = Field(default_factory=dict)
    journal_entries: list[JournalEntry] = Field(default_factory=list)
    protocol_index: dict[str, ProtocolRecord] = Field(default_factory=dict)
    observations: list[ObservationRecord] = Field(default_factory=list)
    session_context_summary: str | None = None
    recent_entities: dict[str, Any] = Field(default_factory=dict)
    recent_results: list[RecentResult] = Field(default_factory=list)
    open_sessions: list[str] = Field(default_factory=list)
    historical_session_summaries: dict[str, str] = Field(default_factory=dict)
    scratch_state: dict[str, Any] = Field(default_factory=dict)
