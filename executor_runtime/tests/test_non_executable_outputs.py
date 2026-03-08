from context_action_plan.parser import parse_transcript
from plan_validation.validator import validate_parsed_output

from executor_runtime.executor import execute_validated_output
from executor_runtime.mock_state import MockRuntime


class _FakeJournalTool:
    def write_entry(
        self, content: str, entry_type: str, metadata: dict, session_id=None
    ):
        del session_id
        return {
            "status": "success",
            "entry_id": "fake-id",
            "entry_type": entry_type,
            "content": content,
            "metadata": metadata,
        }


def test_note_capture_not_executed():
    parsed = parse_transcript("sample 4 became cloudy after heating")
    validation = validate_parsed_output(parsed)

    result = execute_validated_output(parsed, validation, MockRuntime())

    assert result.status.value == "not_executed"
    assert result.executed is False


def test_note_capture_writes_when_journal_tool_configured():
    parsed = parse_transcript("sample 4 became cloudy after heating")
    validation = validate_parsed_output(parsed)

    runtime = MockRuntime(journal_write_tool=_FakeJournalTool())
    result = execute_validated_output(parsed, validation, runtime)

    assert result.status.value == "succeeded"
    assert result.executed is True
    assert result.executed_steps == 1
    assert result.final_output is not None
    assert result.final_output["entry_type"] == "observation"


def test_clarification_not_executed():
    parsed = parse_transcript("take the previous value and write it down")
    validation = validate_parsed_output(parsed)

    result = execute_validated_output(parsed, validation, MockRuntime())

    assert result.status.value == "not_executed"
    assert result.executed is False


def test_validator_non_executable_short_circuit():
    parsed = parse_transcript("hello how are you")
    validation = validate_parsed_output(parsed)

    result = execute_validated_output(parsed, validation, MockRuntime())

    assert result.status.value == "not_executed"
    assert result.executed_steps == 0
