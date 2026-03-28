from context_action_plan.enums import ActionName

from executor_runtime.mock_state import MockRuntime
from executor_runtime.mock_tools import get_tool_handler


def test_convert_tool_success():
    runtime = MockRuntime()
    handler = get_tool_handler(ActionName.CONVERT_UNIT)
    out, err = handler({"value": 5, "from_unit": "liters", "to_unit": "mL"}, runtime)

    assert err is None
    assert out is not None
    assert out["value"] == 5000.0
    assert out["unit"] == "mL"


def test_convert_tool_unsupported_unit():
    runtime = MockRuntime()
    handler = get_tool_handler(ActionName.CONVERT_UNIT)
    out, err = handler({"value": 5, "from_unit": "kg", "to_unit": "mL"}, runtime)

    assert out is None
    assert err is not None
    assert err.code.value == "UNSUPPORTED_UNIT_CONVERSION"


def test_read_calculator_missing_slot():
    runtime = MockRuntime(active_session_exists=True, calculator_slots={})
    handler = get_tool_handler(ActionName.READ_CALCULATOR_RESULT)
    out, err = handler({"slot": 1}, runtime)

    assert out is None
    assert err is not None
    assert err.code.value == "CALCULATOR_SLOT_NOT_FOUND"


def test_write_journal_appends():
    runtime = MockRuntime(active_session_exists=True)
    handler = get_tool_handler(ActionName.WRITE_JOURNAL_ENTRY)
    out, err = handler({"content": "entry"}, runtime)

    assert err is None
    assert out is not None
    assert out["entry_index"] == 0
    assert runtime.journal_entries == ["entry"]
