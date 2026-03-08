"""Validation tests for note_capture outputs."""

from context_action_plan.enums import ActionName, ParseStatus
from context_action_plan.parser import parse_transcript
from context_action_plan.schemas import NoteCapture

from plan_validation.validator import validate_parsed_output


def test_valid_note_capture():
    parsed = parse_transcript("sample 4 became cloudy after heating")
    assert isinstance(parsed, NoteCapture)
    result = validate_parsed_output(parsed)
    assert result.is_valid is True
    assert result.is_executable is False


def test_note_capture_with_empty_content_fails():
    parsed = parse_transcript("sample 4 became cloudy after heating")
    assert isinstance(parsed, NoteCapture)
    broken = parsed.model_copy(
        update={"note": parsed.note.model_copy(update={"content": "   "})}
    )
    result = validate_parsed_output(broken)
    assert result.is_valid is False
    assert any(err.code.value == "INVALID_NOTE_PAYLOAD" for err in result.errors)


def test_note_capture_with_steps_fails():
    parsed = parse_transcript("sample 4 became cloudy after heating")
    assert isinstance(parsed, NoteCapture)
    fake_step = {
        "step_id": "s1",
        "action": ActionName.RECORD_OBSERVATION,
        "args": {"content": "x"},
    }
    broken = parsed.model_copy(update={"steps": [fake_step]})
    result = validate_parsed_output(broken)
    assert result.is_valid is False
    assert any(err.code.value == "INVALID_NOTE_PAYLOAD" for err in result.errors)


def test_note_capture_status_not_ready_fails():
    parsed = parse_transcript("sample 4 became cloudy after heating")
    assert isinstance(parsed, NoteCapture)
    broken = parsed.model_copy(update={"status": ParseStatus.NEEDS_CLARIFICATION})
    result = validate_parsed_output(broken)
    assert result.is_valid is False
    assert any(
        err.code.value == "INVALID_KIND_STATUS_COMBINATION" for err in result.errors
    )
