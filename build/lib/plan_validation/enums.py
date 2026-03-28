"""Enums for plan validation and tool registry contracts."""

from enum import Enum


class ValidationCode(str, Enum):
    """Stable validation error/warning codes."""

    UNKNOWN_ACTION = "UNKNOWN_ACTION"
    MISSING_REQUIRED_ARG = "MISSING_REQUIRED_ARG"
    INVALID_ARG_TYPE = "INVALID_ARG_TYPE"
    INVALID_STEP_REFERENCE = "INVALID_STEP_REFERENCE"
    FORWARD_REFERENCE_NOT_ALLOWED = "FORWARD_REFERENCE_NOT_ALLOWED"
    DUPLICATE_STEP_ID = "DUPLICATE_STEP_ID"
    EMPTY_EXECUTABLE_PLAN = "EMPTY_EXECUTABLE_PLAN"
    INVALID_KIND_STATUS_COMBINATION = "INVALID_KIND_STATUS_COMBINATION"
    NON_EXECUTABLE_OUTPUT = "NON_EXECUTABLE_OUTPUT"
    ENTITY_STEP_MISMATCH = "ENTITY_STEP_MISMATCH"
    INVALID_NOTE_PAYLOAD = "INVALID_NOTE_PAYLOAD"
    INVALID_CLARIFICATION_PAYLOAD = "INVALID_CLARIFICATION_PAYLOAD"
    INVALID_ARG_SHAPE = "INVALID_ARG_SHAPE"
    RECOGNIZED_BUT_UNIMPLEMENTED = "RECOGNIZED_BUT_UNIMPLEMENTED"


class IssueSeverity(str, Enum):
    """Validation issue severity."""

    ERROR = "error"
    WARNING = "warning"


class ToolCategory(str, Enum):
    """Lightweight tool behavior metadata."""

    READ = "read"
    COMPUTE = "compute"
    WRITE = "write"
    SEARCH = "search"


class ValueKind(str, Enum):
    """Supported tool argument value kinds."""

    INT = "int"
    FLOAT = "float"
    NUMBER = "number"
    STR = "str"
    STEP_REF = "step_ref"
    BOOL = "bool"
    DICT = "dict"
