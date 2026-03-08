"""Additional invalid/mixed validation scenarios."""

from context_action_plan.enums import ActionName
from context_action_plan.parser import parse_transcript
from context_action_plan.schemas import ActionPlan

from plan_validation.validator import validate_parsed_output


def test_ready_plan_with_errors_is_marked_non_executable():
    parsed = parse_transcript("look up protocol for PCR cleanup")
    assert isinstance(parsed, ActionPlan)
    broken_step = parsed.steps[0].model_copy(update={"args": {}})
    broken = parsed.model_copy(update={"steps": [broken_step]})
    result = validate_parsed_output(broken)
    assert result.is_valid is False
    assert result.is_executable is False


def test_convert_unit_arg_type_error():
    parsed = parse_transcript("convert 5 liters to milliliters")
    assert isinstance(parsed, ActionPlan)
    bad = parsed.steps[0].model_copy(
        update={"args": {"from_unit": "L", "to_unit": 5, "value": 5}}
    )
    broken = parsed.model_copy(update={"steps": [bad]})
    result = validate_parsed_output(broken)
    assert result.is_valid is False
    assert any(err.code.value == "INVALID_ARG_TYPE" for err in result.errors)


def test_add_constant_binary_shape_validates():
    parsed = parse_transcript("add 2 and 2")
    assert isinstance(parsed, ActionPlan)
    result = validate_parsed_output(parsed)
    assert result.is_valid is True
    assert parsed.steps[0].action == ActionName.ADD_CONSTANT
