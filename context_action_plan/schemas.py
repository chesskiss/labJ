"""Pydantic schemas for transcript parsing output contracts."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from .enums import (
    ActionName,
    IntentName,
    NoteType,
    ParseStatus,
    ResultKind,
    SessionScope,
)


class ScopeInfo(BaseModel):
    """Session scope requested by the user input."""

    session: SessionScope = SessionScope.ACTIVE
    session_ref: Optional[str] = None


class IntentInfo(BaseModel):
    """High-level semantic intent."""

    name: IntentName
    confidence: float = Field(ge=0.0, le=1.0)


class EntityBundle(BaseModel):
    """Extracted entities/slots used to build execution steps."""

    calculator_slot: Optional[int] = None
    operand: Optional[float] = None
    source_unit: Optional[str] = None
    target_unit: Optional[str] = None
    protocol_name: Optional[str] = None
    free_text_value: Optional[str] = None


class ActionStep(BaseModel):
    """A single executor-ready step in the action plan."""

    step_id: str
    action: ActionName
    args: dict[str, Any] = Field(default_factory=dict)


class MissingField(BaseModel):
    """A required field that is missing and blocks execution."""

    field: str
    reason: str


class Ambiguity(BaseModel):
    """A field that has multiple plausible candidates."""

    field: str
    candidates: list[str] = Field(default_factory=list)
    reason: Optional[str] = None


class NotePayload(BaseModel):
    """Structured note output for note capture flows."""

    note_type: NoteType
    content: str


class ActionPlan(BaseModel):
    """Executable action plan output."""

    kind: Literal[ResultKind.ACTION_PLAN] = ResultKind.ACTION_PLAN
    status: ParseStatus = ParseStatus.READY
    user_text: str
    scope: ScopeInfo = Field(default_factory=ScopeInfo)
    intent: IntentInfo
    entities: EntityBundle = Field(default_factory=EntityBundle)
    steps: list[ActionStep] = Field(default_factory=list)
    missing: list[MissingField] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class NoteCapture(BaseModel):
    """Observation/note capture output."""

    kind: Literal[ResultKind.NOTE_CAPTURE] = ResultKind.NOTE_CAPTURE
    status: ParseStatus = ParseStatus.READY
    user_text: str
    scope: ScopeInfo = Field(default_factory=ScopeInfo)
    intent: IntentInfo
    note: NotePayload
    entities: EntityBundle = Field(default_factory=EntityBundle)
    missing: list[MissingField] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)
    steps: list[ActionStep] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ClarificationNeeded(BaseModel):
    """Partially-understood request that requires clarification or is not actionable."""

    kind: Literal[ResultKind.CLARIFICATION_NEEDED] = ResultKind.CLARIFICATION_NEEDED
    status: ParseStatus
    user_text: str
    scope: ScopeInfo = Field(default_factory=ScopeInfo)
    intent: IntentInfo
    entities: EntityBundle = Field(default_factory=EntityBundle)
    missing: list[MissingField] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)
    steps: list[ActionStep] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


ParsedOutput = ActionPlan | NoteCapture | ClarificationNeeded
