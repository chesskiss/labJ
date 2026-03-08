"""Execution schemas for runtime stage."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from context_action_plan.enums import ActionName

from .enums import ExecutionStatus, RuntimeErrorCode


class RuntimeErrorInfo(BaseModel):
    """Structured runtime failure info."""

    code: RuntimeErrorCode
    message: str
    step_id: Optional[str] = None
    action: Optional[ActionName] = None


class ExecutionResult(BaseModel):
    """Structured execution output."""

    status: ExecutionStatus
    executed: bool
    executed_steps: int = 0
    step_results: dict[str, dict[str, Any]] = Field(default_factory=dict)
    final_output: Optional[dict[str, Any]] = None
    error: Optional[RuntimeErrorInfo] = None
    notes: list[str] = Field(default_factory=list)
