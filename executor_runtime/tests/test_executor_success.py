from context_action_plan.parser import parse_transcript
from plan_validation.validator import validate_parsed_output

from executor_runtime.executor import execute_validated_output
from executor_runtime.mock_state import MockRuntime


def test_successful_multi_step_execution():
    parsed = parse_transcript(
        "take result from calculator 1, add 2, convert liters to mL, write to journal"
    )
    validation = validate_parsed_output(parsed)
    runtime = MockRuntime(
        active_session_exists=True,
        calculator_slots={1: {"value": 3.5, "unit": "L"}},
    )

    result = execute_validated_output(parsed, validation, runtime)

    assert result.status.value == "succeeded"
    assert result.executed is True
    assert result.executed_steps == 4
    assert result.step_results["s1"]["value"] == 3.5
    assert result.step_results["s2"]["value"] == 5.5
    assert result.step_results["s3"]["value"] == 5500.0
    assert result.step_results["s3"]["unit"] == "mL"
    assert runtime.journal_entries


def test_protocol_lookup_success():
    parsed = parse_transcript("look up protocol for PCR cleanup")
    validation = validate_parsed_output(parsed)
    runtime = MockRuntime(
        protocol_index={"pcr cleanup": {"title": "PCR Cleanup", "content": "Step 1"}}
    )

    result = execute_validated_output(parsed, validation, runtime)

    assert result.status.value == "succeeded"
    assert result.executed_steps == 1
    assert result.final_output is not None
    assert result.final_output["title"] == "PCR Cleanup"


def test_simple_convert_direct_value_success():
    parsed = parse_transcript("convert 5 liters to milliliters")
    validation = validate_parsed_output(parsed)

    result = execute_validated_output(parsed, validation, MockRuntime())

    assert result.status.value == "succeeded"
    assert result.final_output is not None
    assert result.final_output["value"] == 5000.0
    assert result.final_output["unit"] == "mL"


def test_arithmetic_without_reference_success():
    parsed = parse_transcript("add 2 and 2")
    validation = validate_parsed_output(parsed)

    result = execute_validated_output(parsed, validation, MockRuntime())

    assert result.status.value == "succeeded"
    assert result.final_output is not None
    assert result.final_output["value"] == 4.0


def test_final_output_is_last_step_result():
    parsed = parse_transcript("convert 5 liters to milliliters")
    validation = validate_parsed_output(parsed)
    result = execute_validated_output(parsed, validation, MockRuntime())

    assert result.final_output == result.step_results["s1"]


def test_journal_entry_content_generated_from_previous_steps():
    parsed = parse_transcript("take result from calculator 1, add 2, write to journal")
    validation = validate_parsed_output(parsed)
    runtime = MockRuntime(
        active_session_exists=True, calculator_slots={1: {"value": 3.5, "unit": "L"}}
    )

    result = execute_validated_output(parsed, validation, runtime)

    assert result.status.value == "succeeded"
    assert runtime.journal_entries
    assert "Computed value" in runtime.journal_entries[-1]
