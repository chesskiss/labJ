"""Stable enums for context-to-action-plan parsing."""

from enum import Enum


class ResultKind(str, Enum):
    """Top-level parsed result kinds."""

    ACTION_PLAN = "action_plan"
    NOTE_CAPTURE = "note_capture"
    CLARIFICATION_NEEDED = "clarification_needed"


class ParseStatus(str, Enum):
    """Result status values."""

    READY = "ready"
    NEEDS_CLARIFICATION = "needs_clarification"
    RECOGNIZED_BUT_UNIMPLEMENTED = "recognized_but_unimplemented"
    NOT_A_COMMAND = "not_a_command"
    UNSUPPORTED = "unsupported"


class SessionScope(str, Enum):
    """Supported session scoping modes."""

    ACTIVE = "active"
    SPECIFIC = "specific"
    ALL_OPEN = "all_open"
    HISTORICAL = "historical"


class IntentName(str, Enum):
    """Stable intent names for downstream execution routing."""

    TRANSFORM_AND_RECORD_VALUE = "transform_and_record_value"
    RECORD_OBSERVATION = "record_observation"
    RECORD_VALUE = "record_value"
    RETRIEVE_PROTOCOL = "retrieve_protocol"
    CALCULATOR_OPERATION = "calculator_operation"
    SEARCH_PAST_RESULTS = "search_past_results"
    UNSUPPORTED = "unsupported"


class ActionName(str, Enum):
    """Stable action step names for the executor contract."""

    READ_CALCULATOR_RESULT = "read_calculator_result"
    ADD_CONSTANT = "add_constant"
    SUBTRACT_CONSTANT = "subtract_constant"
    MULTIPLY_CONSTANT = "multiply_constant"
    DIVIDE_CONSTANT = "divide_constant"
    CONVERT_UNIT = "convert_unit"
    WRITE_JOURNAL_ENTRY = "write_journal_entry"
    SEARCH_PROTOCOL = "search_protocol"
    RECORD_OBSERVATION = "record_observation"


class NoteType(str, Enum):
    """Supported note sub-types."""

    OBSERVATION = "observation"
    VALUE = "value"
    GENERAL = "general"
