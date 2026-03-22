import uuid

from context_action_plan.parser import parse_transcript
from plan_validation.validator import validate_parsed_output

from executor_runtime.executor import execute_validated_output
from executor_runtime.mock_state import MockRuntime


class _FakeJournalTool:
    def __init__(self):
        self.last_session_id = None
        self.last_content = None
        self.latest_content = None

    def write_entry(
        self, content: str, entry_type: str, metadata: dict, session_id=None
    ):
        self.last_session_id = session_id
        self.last_content = content
        self.latest_content = content
        return {
            "status": "success",
            "entry_id": "fake-id",
            "entry_type": entry_type,
            "content": content,
            "metadata": metadata,
        }

    def get_latest_session_id(self):
        return None

    def get_latest_entry_content(self, session_id):
        del session_id
        return self.latest_content


class _FakeJournalToolWithLatest(_FakeJournalTool):
    def __init__(self, session_id):
        super().__init__()
        self._session_id = session_id

    def get_latest_session_id(self):
        return self._session_id


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
    assert result.final_output["metadata"]["source"] == "executor_note_capture"
    assert result.final_output["metadata"]["title"].startswith("Session ")


def test_note_capture_uses_latest_session_id_when_available():
    parsed = parse_transcript("sample 4 became cloudy after heating")
    validation = validate_parsed_output(parsed)
    expected_session_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    tool = _FakeJournalToolWithLatest(expected_session_id)

    runtime = MockRuntime(journal_write_tool=tool)
    result = execute_validated_output(parsed, validation, runtime)

    assert result.status.value == "succeeded"
    assert runtime.active_session_id is not None
    assert runtime.active_session_id == expected_session_id
    assert tool.last_session_id == expected_session_id
    assert result.final_output is not None
    assert (
        result.final_output["metadata"]["title"]
        == f"Session {str(expected_session_id).split('-')[0]}"
    )


def test_note_capture_appends_to_existing_session_content():
    first = parse_transcript("sample 4 became cloudy after heating")
    second = parse_transcript("sample 4 became clearer after cooling")
    first_validation = validate_parsed_output(first)
    second_validation = validate_parsed_output(second)
    tool = _FakeJournalTool()
    runtime = MockRuntime(journal_write_tool=tool)

    first_result = execute_validated_output(first, first_validation, runtime)
    assert first_result.status.value == "succeeded"
    assert tool.last_content == "sample 4 became cloudy after heating"

    second_result = execute_validated_output(second, second_validation, runtime)
    assert second_result.status.value == "succeeded"
    assert (
        tool.last_content
        == "sample 4 became cloudy after heating\nsample 4 became clearer after cooling"
    )


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
