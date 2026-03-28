"""Validation tests for clarification_needed outputs."""

from context_action_plan.enums import ParseStatus
from context_action_plan.parser import parse_transcript
from context_action_plan.schemas import ClarificationNeeded

from plan_validation.validator import validate_parsed_output


def test_valid_clarification_needed():
    parsed = parse_transcript("take the previous value and write it down")
    assert isinstance(parsed, ClarificationNeeded)
    result = validate_parsed_output(parsed)
    assert result.is_valid is True
    assert result.is_executable is False


def test_valid_not_a_command_output():
    parsed = parse_transcript("hello how are you")
    assert isinstance(parsed, ClarificationNeeded)
    result = validate_parsed_output(parsed)
    assert result.is_valid is True
    assert result.is_executable is False


def test_clarification_with_ready_status_fails():
    parsed = parse_transcript("take the previous value and write it down")
    assert isinstance(parsed, ClarificationNeeded)
    broken = parsed.model_copy(update={"status": ParseStatus.READY})
    result = validate_parsed_output(broken)
    assert result.is_valid is False
    assert any(
        err.code.value == "INVALID_KIND_STATUS_COMBINATION" for err in result.errors
    )


def test_clarification_with_steps_fails():
    parsed = parse_transcript("take the previous value and write it down")
    assert isinstance(parsed, ClarificationNeeded)
    broken = parsed.model_copy(
        update={"steps": [{"step_id": "s1", "action": "add_constant", "args": {}}]}
    )
    result = validate_parsed_output(broken)
    assert result.is_valid is False
    assert any(
        err.code.value == "INVALID_CLARIFICATION_PAYLOAD" for err in result.errors
    )


def test_needs_clarification_without_missing_or_ambiguities_fails():
    parsed = parse_transcript("take the previous value and write it down")
    assert isinstance(parsed, ClarificationNeeded)
    broken = parsed.model_copy(update={"missing": [], "ambiguities": []})
    result = validate_parsed_output(broken)
    assert result.is_valid is False
    assert any(
        err.code.value == "INVALID_CLARIFICATION_PAYLOAD" for err in result.errors
    )
