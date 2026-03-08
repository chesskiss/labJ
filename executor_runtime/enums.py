"""Enums for executor runtime status and errors."""

from enum import Enum


class ExecutionStatus(str, Enum):
    """Execution result status."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    NOT_EXECUTED = "not_executed"


class RuntimeErrorCode(str, Enum):
    """Stable runtime error codes."""

    CALCULATOR_SLOT_NOT_FOUND = "CALCULATOR_SLOT_NOT_FOUND"
    NO_ACTIVE_SESSION = "NO_ACTIVE_SESSION"
    UNSUPPORTED_UNIT_CONVERSION = "UNSUPPORTED_UNIT_CONVERSION"
    DIVISION_BY_ZERO = "DIVISION_BY_ZERO"
    PROTOCOL_NOT_FOUND = "PROTOCOL_NOT_FOUND"
    INVALID_REFERENCE_RESOLUTION = "INVALID_REFERENCE_RESOLUTION"
    TOOL_EXECUTION_ERROR = "TOOL_EXECUTION_ERROR"
