"""Validation logic for parsed outputs and executable action plans."""

from __future__ import annotations

from typing import Any

from context_action_plan.enums import ActionName, ParseStatus, ResultKind
from context_action_plan.schemas import (
    ActionPlan,
    ClarificationNeeded,
    NoteCapture,
    ParsedOutput,
)

from .enums import IssueSeverity, ValidationCode, ValueKind
from .registry import build_default_registry
from .schemas import ToolRegistry, ToolSpec, ValidationIssue, ValidationResult


def validate_parsed_output(
    parsed: ParsedOutput, registry: ToolRegistry | None = None
) -> ValidationResult:
    """Validate top-level parsed output according to kind-specific rules."""
    reg = registry or build_default_registry()
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    if isinstance(parsed, ActionPlan):
        _validate_action_plan(parsed, reg, errors, warnings)
        return _finalize(parsed.kind, errors, warnings, parsed)

    if isinstance(parsed, NoteCapture):
        _validate_note_capture(parsed, errors, warnings)
        return _finalize(parsed.kind, errors, warnings, parsed)

    if isinstance(parsed, ClarificationNeeded):
        _validate_clarification(parsed, errors, warnings)
        return _finalize(parsed.kind, errors, warnings, parsed)

    errors.append(
        ValidationIssue(
            code=ValidationCode.NON_EXECUTABLE_OUTPUT,
            severity=IssueSeverity.ERROR,
            message="unknown parsed output type",
        )
    )
    return ValidationResult(
        is_valid=False,
        is_executable=False,
        errors=errors,
        warnings=warnings,
    )


def validate_action_plan(
    plan: ActionPlan, registry: ToolRegistry | None = None
) -> ValidationResult:
    """Validate an action plan against tool registry contracts."""
    return validate_parsed_output(plan, registry=registry)


def _validate_action_plan(
    plan: ActionPlan,
    registry: ToolRegistry,
    errors: list[ValidationIssue],
    warnings: list[ValidationIssue],
) -> None:
    if plan.status == ParseStatus.RECOGNIZED_BUT_UNIMPLEMENTED:
        warnings.append(
            ValidationIssue(
                code=ValidationCode.RECOGNIZED_BUT_UNIMPLEMENTED,
                severity=IssueSeverity.WARNING,
                message="request was understood but no implemented tool currently supports it",
                field="status",
            )
        )
        if plan.steps:
            warnings.append(
                ValidationIssue(
                    code=ValidationCode.NON_EXECUTABLE_OUTPUT,
                    severity=IssueSeverity.WARNING,
                    message="recognized_but_unimplemented output should not include executable steps",
                    field="steps",
                )
            )
        return

    if plan.status != ParseStatus.READY:
        errors.append(
            ValidationIssue(
                code=ValidationCode.INVALID_KIND_STATUS_COMBINATION,
                severity=IssueSeverity.ERROR,
                message=f"action_plan must be status={ParseStatus.READY.value}",
                field="status",
            )
        )

    if plan.status == ParseStatus.READY and not plan.steps:
        errors.append(
            ValidationIssue(
                code=ValidationCode.EMPTY_EXECUTABLE_PLAN,
                severity=IssueSeverity.ERROR,
                message="ready action_plan must contain at least one step",
                field="steps",
            )
        )

    seen_step_ids: set[str] = set()
    step_order: dict[str, int] = {}
    first_read_slot: int | None = None

    for idx, step in enumerate(plan.steps):
        if step.step_id in seen_step_ids:
            errors.append(
                ValidationIssue(
                    code=ValidationCode.DUPLICATE_STEP_ID,
                    severity=IssueSeverity.ERROR,
                    message=f"duplicate step_id {step.step_id}",
                    field=f"steps[{idx}].step_id",
                    step_id=step.step_id,
                )
            )
        seen_step_ids.add(step.step_id)
        step_order[step.step_id] = idx

        spec = registry.get(step.action)
        if spec is None:
            errors.append(
                ValidationIssue(
                    code=ValidationCode.UNKNOWN_ACTION,
                    severity=IssueSeverity.ERROR,
                    message=f"unknown action {step.action}",
                    field=f"steps[{idx}].action",
                    step_id=step.step_id,
                )
            )
            continue

        if not isinstance(step.args, dict):
            errors.append(
                ValidationIssue(
                    code=ValidationCode.INVALID_ARG_SHAPE,
                    severity=IssueSeverity.ERROR,
                    message="step args must be a dictionary",
                    field=f"steps[{idx}].args",
                    step_id=step.step_id,
                )
            )
            continue

        _validate_step_required_and_types(step.step_id, idx, step.args, spec, errors)
        _validate_step_refs(step.step_id, idx, step.args, step_order, errors)
        _validate_action_specific_rules(
            step.step_id, idx, step.action, step.args, errors
        )

        if step.action == ActionName.READ_CALCULATOR_RESULT:
            slot_val = step.args.get("slot")
            if isinstance(slot_val, int):
                first_read_slot = slot_val

    if plan.entities.calculator_slot is not None and first_read_slot is not None:
        if plan.entities.calculator_slot != first_read_slot:
            errors.append(
                ValidationIssue(
                    code=ValidationCode.ENTITY_STEP_MISMATCH,
                    severity=IssueSeverity.ERROR,
                    message="entities.calculator_slot conflicts with step slot",
                    field="entities.calculator_slot",
                    step_id="s1",
                )
            )

    if plan.status == ParseStatus.READY and errors:
        warnings.append(
            ValidationIssue(
                code=ValidationCode.NON_EXECUTABLE_OUTPUT,
                severity=IssueSeverity.WARNING,
                message="plan marked ready but contains validation errors",
            )
        )


def _validate_note_capture(
    note: NoteCapture,
    errors: list[ValidationIssue],
    warnings: list[ValidationIssue],
) -> None:
    if note.status != ParseStatus.READY:
        errors.append(
            ValidationIssue(
                code=ValidationCode.INVALID_KIND_STATUS_COMBINATION,
                severity=IssueSeverity.ERROR,
                message="note_capture should be status=ready",
                field="status",
            )
        )

    if not note.note.content or not note.note.content.strip():
        errors.append(
            ValidationIssue(
                code=ValidationCode.INVALID_NOTE_PAYLOAD,
                severity=IssueSeverity.ERROR,
                message="note content must be non-empty",
                field="note.content",
            )
        )

    if note.steps:
        errors.append(
            ValidationIssue(
                code=ValidationCode.INVALID_NOTE_PAYLOAD,
                severity=IssueSeverity.ERROR,
                message="note_capture must not include executable steps",
                field="steps",
            )
        )

    if note.missing or note.ambiguities:
        warnings.append(
            ValidationIssue(
                code=ValidationCode.INVALID_NOTE_PAYLOAD,
                severity=IssueSeverity.WARNING,
                message="note_capture includes missing/ambiguity fields; usually unexpected",
            )
        )


def _validate_clarification(
    clar: ClarificationNeeded,
    errors: list[ValidationIssue],
    warnings: list[ValidationIssue],
) -> None:
    if clar.status == ParseStatus.READY:
        errors.append(
            ValidationIssue(
                code=ValidationCode.INVALID_KIND_STATUS_COMBINATION,
                severity=IssueSeverity.ERROR,
                message="clarification_needed cannot be status=ready",
                field="status",
            )
        )

    if clar.status not in {
        ParseStatus.NEEDS_CLARIFICATION,
        ParseStatus.NOT_A_COMMAND,
        ParseStatus.UNSUPPORTED,
    }:
        errors.append(
            ValidationIssue(
                code=ValidationCode.INVALID_KIND_STATUS_COMBINATION,
                severity=IssueSeverity.ERROR,
                message="invalid clarification status",
                field="status",
            )
        )

    if clar.steps:
        errors.append(
            ValidationIssue(
                code=ValidationCode.INVALID_CLARIFICATION_PAYLOAD,
                severity=IssueSeverity.ERROR,
                message="clarification outputs should not contain executable steps",
                field="steps",
            )
        )

    if clar.status == ParseStatus.NEEDS_CLARIFICATION and not (
        clar.missing or clar.ambiguities
    ):
        errors.append(
            ValidationIssue(
                code=ValidationCode.INVALID_CLARIFICATION_PAYLOAD,
                severity=IssueSeverity.ERROR,
                message="needs_clarification requires missing and/or ambiguities",
                field="missing",
            )
        )

    if (
        clar.status in {ParseStatus.NOT_A_COMMAND, ParseStatus.UNSUPPORTED}
        and not clar.notes
    ):
        warnings.append(
            ValidationIssue(
                code=ValidationCode.INVALID_CLARIFICATION_PAYLOAD,
                severity=IssueSeverity.WARNING,
                message="non-command clarifications should include explanatory notes",
            )
        )


def _validate_step_required_and_types(
    step_id: str,
    step_idx: int,
    args: dict[str, Any],
    spec: ToolSpec,
    errors: list[ValidationIssue],
) -> None:
    known_specs = spec.arg_spec_map()

    for req in spec.required_args:
        if req.name not in args:
            errors.append(
                ValidationIssue(
                    code=ValidationCode.MISSING_REQUIRED_ARG,
                    severity=IssueSeverity.ERROR,
                    message=f"{spec.name.value} requires arg '{req.name}'",
                    field=f"steps[{step_idx}].args.{req.name}",
                    step_id=step_id,
                )
            )

    for group in spec.one_of:
        if not any(name in args for name in group):
            errors.append(
                ValidationIssue(
                    code=ValidationCode.MISSING_REQUIRED_ARG,
                    severity=IssueSeverity.ERROR,
                    message=f"{spec.name.value} requires one of {group}",
                    field=f"steps[{step_idx}].args",
                    step_id=step_id,
                )
            )

    for arg_name, arg_value in args.items():
        arg_spec = known_specs.get(arg_name)
        if arg_spec is None:
            continue
        if not _matches_value_kind(arg_value, arg_spec.kind):
            errors.append(
                ValidationIssue(
                    code=ValidationCode.INVALID_ARG_TYPE,
                    severity=IssueSeverity.ERROR,
                    message=f"arg '{arg_name}' expected {arg_spec.kind.value}",
                    field=f"steps[{step_idx}].args.{arg_name}",
                    step_id=step_id,
                )
            )


def _validate_step_refs(
    step_id: str,
    step_idx: int,
    args: dict[str, Any],
    step_order: dict[str, int],
    errors: list[ValidationIssue],
) -> None:
    for arg_name, arg_value in args.items():
        if not arg_name.endswith("_from"):
            continue
        if not isinstance(arg_value, str):
            errors.append(
                ValidationIssue(
                    code=ValidationCode.INVALID_ARG_TYPE,
                    severity=IssueSeverity.ERROR,
                    message=f"reference arg '{arg_name}' must be a step id string",
                    field=f"steps[{step_idx}].args.{arg_name}",
                    step_id=step_id,
                )
            )
            continue
        if arg_value not in step_order:
            errors.append(
                ValidationIssue(
                    code=ValidationCode.INVALID_STEP_REFERENCE,
                    severity=IssueSeverity.ERROR,
                    message=f"unknown referenced step '{arg_value}'",
                    field=f"steps[{step_idx}].args.{arg_name}",
                    step_id=step_id,
                )
            )
            continue
        if step_order[arg_value] >= step_idx:
            errors.append(
                ValidationIssue(
                    code=ValidationCode.FORWARD_REFERENCE_NOT_ALLOWED,
                    severity=IssueSeverity.ERROR,
                    message=f"step '{step_id}' cannot reference forward step '{arg_value}'",
                    field=f"steps[{step_idx}].args.{arg_name}",
                    step_id=step_id,
                )
            )


def _validate_action_specific_rules(
    step_id: str,
    step_idx: int,
    action: ActionName,
    args: dict[str, Any],
    errors: list[ValidationIssue],
) -> None:
    if action == ActionName.CONVERT_UNIT:
        if "value" not in args and "value_from" not in args:
            errors.append(
                ValidationIssue(
                    code=ValidationCode.MISSING_REQUIRED_ARG,
                    severity=IssueSeverity.ERROR,
                    message="convert_unit requires value or value_from",
                    field=f"steps[{step_idx}].args",
                    step_id=step_id,
                )
            )

    if action == ActionName.ADD_CONSTANT:
        has_chain = "value_from" in args and "operand" in args
        has_binary = "left" in args and "right" in args
        if not (has_chain or has_binary):
            errors.append(
                ValidationIssue(
                    code=ValidationCode.MISSING_REQUIRED_ARG,
                    severity=IssueSeverity.ERROR,
                    message="add_constant requires (value_from+operand) or (left+right)",
                    field=f"steps[{step_idx}].args",
                    step_id=step_id,
                )
            )

    if action == ActionName.WRITE_JOURNAL_ENTRY and "value_from" in args:
        ref = args["value_from"]
        if not isinstance(ref, str):
            errors.append(
                ValidationIssue(
                    code=ValidationCode.INVALID_ARG_TYPE,
                    severity=IssueSeverity.ERROR,
                    message="write_journal_entry value_from must be a step id string",
                    field=f"steps[{step_idx}].args.value_from",
                    step_id=step_id,
                )
            )


def _matches_value_kind(value: Any, kind: ValueKind) -> bool:
    if kind == ValueKind.INT:
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == ValueKind.FLOAT:
        return isinstance(value, float)
    if kind == ValueKind.NUMBER:
        return (isinstance(value, int) and not isinstance(value, bool)) or isinstance(
            value, float
        )
    if kind == ValueKind.STR:
        return isinstance(value, str)
    if kind == ValueKind.STEP_REF:
        return isinstance(value, str) and value.startswith("s")
    if kind == ValueKind.BOOL:
        return isinstance(value, bool)
    if kind == ValueKind.DICT:
        return isinstance(value, dict)
    return False


def _finalize(
    kind: ResultKind | None,
    errors: list[ValidationIssue],
    warnings: list[ValidationIssue],
    parsed: ParsedOutput | None = None,
) -> ValidationResult:
    is_valid = len([e for e in errors if e.severity == IssueSeverity.ERROR]) == 0
    is_executable = bool(
        is_valid
        and parsed is not None
        and isinstance(parsed, ActionPlan)
        and parsed.status == ParseStatus.READY
        and len(parsed.steps) > 0
    )
    normalized = parsed.model_dump() if parsed is not None else None
    return ValidationResult(
        is_valid=is_valid,
        is_executable=is_executable,
        normalized_kind=kind,
        errors=errors,
        warnings=warnings,
        normalized=normalized,
    )
