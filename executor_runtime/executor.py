"""Validated-plan executor against mocked runtime tools."""

from __future__ import annotations

import uuid

from context_action_plan.enums import ParseStatus
from context_action_plan.schemas import (
    ActionPlan,
    ClarificationNeeded,
    NoteCapture,
    ParsedOutput,
)
from plan_validation.schemas import ValidationResult

from .enums import ExecutionStatus, RuntimeErrorCode
from .mock_state import MockRuntime
from .mock_tools import get_tool_handler
from .resolver import resolve_step_args
from .schemas import ExecutionResult, RuntimeErrorInfo


def execute_validated_output(
    parsed: ParsedOutput,
    validation: ValidationResult,
    runtime: MockRuntime,
) -> ExecutionResult:
    """Execute parsed output only when validator marks it executable."""
    if isinstance(parsed, NoteCapture):
        return _handle_note_capture(parsed, validation, runtime)

    if not validation.is_executable:
        return ExecutionResult(
            status=ExecutionStatus.NOT_EXECUTED,
            executed=False,
            executed_steps=0,
            notes=["Validation marked output as non-executable"],
        )

    if isinstance(parsed, ActionPlan):
        return execute_action_plan(parsed, runtime)

    if isinstance(parsed, ClarificationNeeded):
        return ExecutionResult(
            status=ExecutionStatus.NOT_EXECUTED,
            executed=False,
            executed_steps=0,
            notes=["Parsed output requires clarification and is not executable"],
        )

    return ExecutionResult(
        status=ExecutionStatus.NOT_EXECUTED,
        executed=False,
        executed_steps=0,
        notes=["Parsed output type is not supported by executor"],
    )


def _handle_note_capture(
    parsed: NoteCapture, validation: ValidationResult, runtime: MockRuntime
) -> ExecutionResult:
    if not validation.is_valid:
        return ExecutionResult(
            status=ExecutionStatus.NOT_EXECUTED,
            executed=False,
            executed_steps=0,
            notes=["NoteCapture is not valid and cannot be persisted"],
        )

    if runtime.journal_write_tool is None:
        return ExecutionResult(
            status=ExecutionStatus.NOT_EXECUTED,
            executed=False,
            executed_steps=0,
            notes=["Parsed output is note_capture and no journal tool is configured"],
        )

    try:
        session_id = _resolve_note_capture_session_id(runtime)
        result = runtime.journal_write_tool.write_entry(
            content=parsed.note.content,
            entry_type=parsed.note.note_type.value,
            metadata={
                "source": "note_capture",
                "intent": parsed.intent.name.value,
                "status": parsed.status.value,
            },
            session_id=session_id,
        )
    except Exception as exc:  # pragma: no cover
        return ExecutionResult(
            status=ExecutionStatus.FAILED,
            executed=True,
            executed_steps=0,
            error=RuntimeErrorInfo(
                code=RuntimeErrorCode.TOOL_EXECUTION_ERROR,
                message=f"note capture persistence failed: {exc}",
                action="write_journal_entry",
            ),
            notes=[],
        )

    return ExecutionResult(
        status=ExecutionStatus.SUCCEEDED,
        executed=True,
        executed_steps=1,
        step_results={"note_capture_write": result},
        final_output=result,
        notes=[],
    )


def _resolve_note_capture_session_id(runtime: MockRuntime) -> uuid.UUID:
    """Resolve a deterministic session id for note-capture persistence."""
    if runtime.active_session_id is not None:
        return runtime.active_session_id

    latest_session_id: uuid.UUID | None = None
    resolver = getattr(runtime.journal_write_tool, "get_latest_session_id", None)
    if callable(resolver):
        try:
            resolved = resolver()
            if isinstance(resolved, uuid.UUID):
                latest_session_id = resolved
        except Exception:
            latest_session_id = None

    runtime.active_session_id = latest_session_id or uuid.uuid4()
    return runtime.active_session_id


def execute_action_plan(plan: ActionPlan, runtime: MockRuntime) -> ExecutionResult:
    """Execute a structurally valid action plan against mocked runtime state."""
    if plan.status != ParseStatus.READY:
        return ExecutionResult(
            status=ExecutionStatus.NOT_EXECUTED,
            executed=False,
            executed_steps=0,
            notes=["Action plan status is not ready"],
        )

    step_results: dict[str, dict] = {}

    for step in plan.steps:
        resolved_args, resolve_error = resolve_step_args(step.args, step_results)
        if resolve_error:
            return _failed_result(
                step_results, resolve_error, step.step_id, step.action.value
            )

        try:
            handler = get_tool_handler(step.action)
            tool_result, runtime_error = handler(resolved_args or {}, runtime)
        except Exception as exc:  # pragma: no cover
            runtime_error = RuntimeErrorInfo(
                code=RuntimeErrorCode.TOOL_EXECUTION_ERROR,
                message=f"tool execution exception: {exc}",
            )
            tool_result = None

        if runtime_error:
            return _failed_result(
                step_results, runtime_error, step.step_id, step.action.value
            )

        step_results[step.step_id] = tool_result or {}

    final_output = step_results[plan.steps[-1].step_id] if plan.steps else None
    return ExecutionResult(
        status=ExecutionStatus.SUCCEEDED,
        executed=True,
        executed_steps=len(step_results),
        step_results=step_results,
        final_output=final_output,
        notes=[],
    )


def _failed_result(
    step_results: dict[str, dict],
    error: RuntimeErrorInfo,
    step_id: str,
    action: str,
) -> ExecutionResult:
    enriched_error = RuntimeErrorInfo(
        code=error.code,
        message=error.message,
        step_id=step_id,
        action=action,
    )
    return ExecutionResult(
        status=ExecutionStatus.FAILED,
        executed=True,
        executed_steps=len(step_results),
        step_results=step_results,
        final_output=None,
        error=enriched_error,
        notes=[],
    )
