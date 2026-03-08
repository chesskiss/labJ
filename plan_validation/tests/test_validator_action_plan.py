"""Validation tests for action_plan outputs."""

from context_action_plan.enums import ActionName
from context_action_plan.parser import parse_transcript
from context_action_plan.schemas import ActionPlan

from plan_validation.validator import validate_parsed_output


def test_valid_transform_plan_is_executable():
    parsed = parse_transcript(
        "take result from calculator 1, add 2, convert liters to mL, write to journal"
    )
    assert isinstance(parsed, ActionPlan)
    result = validate_parsed_output(parsed)
    assert result.is_valid is True
    assert result.is_executable is True
    assert result.errors == []


def test_valid_protocol_lookup_plan():
    parsed = parse_transcript("look up protocol for PCR cleanup")
    result = validate_parsed_output(parsed)
    assert result.is_valid is True
    assert result.is_executable is True


def test_recognized_but_unimplemented_is_valid_non_executable():
    parsed = parse_transcript("calculate sine of 2")
    assert isinstance(parsed, ActionPlan)
    result = validate_parsed_output(parsed)
    assert result.is_valid is True
    assert result.is_executable is False
    assert any(w.code.value == "RECOGNIZED_BUT_UNIMPLEMENTED" for w in result.warnings)


def test_simulation_request_recognized_but_unimplemented_is_valid_non_executable():
    parsed = parse_transcript("create a 3d simulation")
    assert isinstance(parsed, ActionPlan)
    result = validate_parsed_output(parsed)
    assert result.is_valid is True
    assert result.is_executable is False
    assert any(w.code.value == "RECOGNIZED_BUT_UNIMPLEMENTED" for w in result.warnings)


def test_ready_action_plan_with_no_steps_fails():
    parsed = parse_transcript("look up protocol for PCR cleanup")
    assert isinstance(parsed, ActionPlan)
    broken = parsed.model_copy(update={"steps": []})
    result = validate_parsed_output(broken)
    assert result.is_valid is False
    assert any(err.code.value == "EMPTY_EXECUTABLE_PLAN" for err in result.errors)


def test_duplicate_step_ids_fail():
    parsed = parse_transcript(
        "take result from calculator 1, add 2, convert liters to mL, write to journal"
    )
    assert isinstance(parsed, ActionPlan)
    s1 = parsed.steps[0].model_copy(update={"step_id": "dup"})
    s2 = parsed.steps[1].model_copy(update={"step_id": "dup"})
    broken = parsed.model_copy(update={"steps": [s1, s2, *parsed.steps[2:]]})
    result = validate_parsed_output(broken)
    assert result.is_valid is False
    assert any(err.code.value == "DUPLICATE_STEP_ID" for err in result.errors)


def test_convert_unit_without_value_or_value_from_fails():
    parsed = parse_transcript("convert 5 liters to milliliters")
    assert isinstance(parsed, ActionPlan)
    broken_step = parsed.steps[0].model_copy(
        update={"args": {"from_unit": "L", "to_unit": "mL"}}
    )
    broken = parsed.model_copy(update={"steps": [broken_step]})
    result = validate_parsed_output(broken)
    assert result.is_valid is False
    assert any(err.code.value == "MISSING_REQUIRED_ARG" for err in result.errors)


def test_entity_step_mismatch_for_calculator_slot():
    parsed = parse_transcript("take result from calculator 1, add 2")
    assert isinstance(parsed, ActionPlan)
    step0 = parsed.steps[0].model_copy(update={"args": {"slot": 2}})
    broken = parsed.model_copy(update={"steps": [step0, *parsed.steps[1:]]})
    result = validate_parsed_output(broken)
    assert result.is_valid is False
    assert any(err.code.value == "ENTITY_STEP_MISMATCH" for err in result.errors)


def test_write_journal_reference_must_point_to_previous():
    parsed = parse_transcript(
        "take result from calculator 1, add 2, convert liters to mL, write to journal"
    )
    assert isinstance(parsed, ActionPlan)
    s4 = parsed.steps[-1].model_copy(
        update={
            "args": {"content_mode": "auto_from_previous_steps", "value_from": "s99"}
        }
    )
    broken = parsed.model_copy(update={"steps": [*parsed.steps[:-1], s4]})
    result = validate_parsed_output(broken)
    assert result.is_valid is False
    assert any(err.code.value == "INVALID_STEP_REFERENCE" for err in result.errors)


def test_add_constant_requires_valid_shape():
    parsed = parse_transcript("take result from calculator 1, add 2")
    assert isinstance(parsed, ActionPlan)
    add_step = parsed.steps[1].model_copy(update={"args": {"value_from": "s1"}})
    broken = parsed.model_copy(update={"steps": [parsed.steps[0], add_step]})
    result = validate_parsed_output(broken)
    assert result.is_valid is False
    assert any(err.code.value == "MISSING_REQUIRED_ARG" for err in result.errors)


def test_forward_reference_not_allowed():
    parsed = parse_transcript("take result from calculator 1, add 2")
    assert isinstance(parsed, ActionPlan)
    add_step = parsed.steps[1].model_copy(
        update={"args": {"value_from": "s2", "operand": 2.0}}
    )
    broken = parsed.model_copy(update={"steps": [parsed.steps[0], add_step]})
    result = validate_parsed_output(broken)
    assert result.is_valid is False
    assert any(
        err.code.value == "FORWARD_REFERENCE_NOT_ALLOWED" for err in result.errors
    )


def test_unknown_action_fails():
    parsed = parse_transcript("look up protocol for PCR cleanup")
    assert isinstance(parsed, ActionPlan)
    step = parsed.steps[0].model_construct(step_id="s1", action="bad_action", args={})  # type: ignore[arg-type]
    broken = parsed.model_copy(update={"steps": [step]})
    result = validate_parsed_output(broken)
    assert result.is_valid is False
    assert any(err.code.value == "UNKNOWN_ACTION" for err in result.errors)


def test_malformed_args_shape_fails():
    parsed = parse_transcript("look up protocol for PCR cleanup")
    assert isinstance(parsed, ActionPlan)
    step = parsed.steps[0].model_construct(
        step_id="s1",
        action=ActionName.SEARCH_PROTOCOL,
        args=["not", "a", "dict"],  # type: ignore[arg-type]
    )
    broken = parsed.model_copy(update={"steps": [step]})
    result = validate_parsed_output(broken)
    assert result.is_valid is False
    assert any(err.code.value == "INVALID_ARG_SHAPE" for err in result.errors)
