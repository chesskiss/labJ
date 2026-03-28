from context_action_plan.parser import parse_transcript
from context_action_plan.schemas import ActionPlan, ActionStep, EntityBundle, IntentInfo
from context_action_plan.enums import ActionName, IntentName
from plan_validation.validator import validate_parsed_output

from executor_runtime.executor import execute_action_plan, execute_validated_output
from executor_runtime.mock_state import MockRuntime


def test_missing_calculator_slot_runtime_failure():
    parsed = parse_transcript(
        "take result from calculator 1, add 2, convert liters to mL, write to journal"
    )
    validation = validate_parsed_output(parsed)
    runtime = MockRuntime(active_session_exists=True, calculator_slots={})

    result = execute_validated_output(parsed, validation, runtime)

    assert result.status.value == "failed"
    assert result.error is not None
    assert result.error.code.value == "CALCULATOR_SLOT_NOT_FOUND"
    assert result.error.step_id == "s1"


def test_protocol_not_found_failure():
    parsed = parse_transcript("look up protocol for PCR cleanup")
    validation = validate_parsed_output(parsed)
    runtime = MockRuntime(protocol_index={})

    result = execute_validated_output(parsed, validation, runtime)

    assert result.status.value == "failed"
    assert result.error is not None
    assert result.error.code.value == "PROTOCOL_NOT_FOUND"


def test_unsupported_unit_conversion_failure():
    parsed = parse_transcript("convert 5 liters to moles")
    validation = validate_parsed_output(parsed)

    result = execute_validated_output(parsed, validation, MockRuntime())

    assert result.status.value == "failed"
    assert result.error is not None
    assert result.error.code.value == "UNSUPPORTED_UNIT_CONVERSION"


def test_bad_reference_resolution_failure():
    parsed = ActionPlan(
        user_text="convert from missing reference",
        intent=IntentInfo(name=IntentName.CALCULATOR_OPERATION, confidence=0.95),
        entities=EntityBundle(source_unit="L", target_unit="mL"),
        steps=[
            ActionStep(
                step_id="s1",
                action=ActionName.CONVERT_UNIT,
                args={"from_unit": "L", "to_unit": "mL", "value_from": "s99"},
            )
        ],
    )

    result = execute_action_plan(parsed, MockRuntime())

    assert result.status.value == "failed"
    assert result.error is not None
    assert result.error.code.value == "INVALID_REFERENCE_RESOLUTION"


def test_divide_by_zero_failure():
    parsed = parse_transcript("take result from calculator 1, divide by 0")
    validation = validate_parsed_output(parsed)
    runtime = MockRuntime(
        active_session_exists=True, calculator_slots={1: {"value": 10.0, "unit": "mL"}}
    )

    result = execute_validated_output(parsed, validation, runtime)

    assert result.status.value == "failed"
    assert result.error is not None
    assert result.error.code.value == "DIVISION_BY_ZERO"


def test_no_active_session_for_journal_write_failure():
    parsed = parse_transcript("take result from calculator 1, add 2, write to journal")
    validation = validate_parsed_output(parsed)
    runtime = MockRuntime(
        active_session_exists=False, calculator_slots={1: {"value": 1.0, "unit": "L"}}
    )

    result = execute_validated_output(parsed, validation, runtime)

    assert result.status.value == "failed"
    assert result.error is not None
    assert result.error.code.value == "NO_ACTIVE_SESSION"


def test_step_results_stop_on_first_failure():
    parsed = parse_transcript(
        "take result from calculator 1, divide by 0, write to journal"
    )
    validation = validate_parsed_output(parsed)
    runtime = MockRuntime(
        active_session_exists=True, calculator_slots={1: {"value": 10.0, "unit": "mL"}}
    )

    result = execute_validated_output(parsed, validation, runtime)

    assert result.status.value == "failed"
    assert result.executed_steps == 1
    assert "s1" in result.step_results
    assert "s2" not in result.step_results
