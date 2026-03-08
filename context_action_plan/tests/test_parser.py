"""Unit tests for deterministic transcript parser."""

from context_action_plan.enums import ActionName, IntentName, ParseStatus, ResultKind
from context_action_plan.parser import parse_transcript
from context_action_plan.schemas import ActionPlan, ClarificationNeeded, NoteCapture


def test_transform_and_record_value_pipeline():
    result = parse_transcript(
        "take result from calculator 1, add 2, convert liters to mL, write to journal"
    )
    assert isinstance(result, ActionPlan)
    assert result.kind == ResultKind.ACTION_PLAN
    assert result.intent.name == IntentName.TRANSFORM_AND_RECORD_VALUE
    assert [s.action for s in result.steps] == [
        ActionName.READ_CALCULATOR_RESULT,
        ActionName.ADD_CONSTANT,
        ActionName.CONVERT_UNIT,
        ActionName.WRITE_JOURNAL_ENTRY,
    ]
    assert result.entities.calculator_slot == 1
    assert result.entities.source_unit == "L"
    assert result.entities.target_unit == "mL"


def test_write_down_result_note_capture():
    result = parse_transcript("write down result 5.2 milliliters")
    assert isinstance(result, NoteCapture)
    assert result.kind == ResultKind.NOTE_CAPTURE
    assert result.intent.name == IntentName.RECORD_VALUE
    assert "5.2" in result.note.content


def test_protocol_lookup_plan():
    result = parse_transcript("look up protocol for PCR cleanup")
    assert isinstance(result, ActionPlan)
    assert result.intent.name == IntentName.RETRIEVE_PROTOCOL
    assert result.steps[0].action == ActionName.SEARCH_PROTOCOL
    assert result.entities.protocol_name == "pcr cleanup"


def test_observation_note_capture():
    result = parse_transcript("sample 4 became cloudy after heating")
    assert isinstance(result, NoteCapture)
    assert result.intent.name == IntentName.RECORD_OBSERVATION


def test_ambiguous_previous_value_needs_clarification():
    result = parse_transcript("take the previous value and write it down")
    assert isinstance(result, ClarificationNeeded)
    assert result.status == ParseStatus.NEEDS_CLARIFICATION
    assert result.missing[0].field == "source_value"
    assert len(result.ambiguities[0].candidates) >= 2


def test_convert_literal_value():
    result = parse_transcript("convert 5 liters to milliliters")
    assert isinstance(result, ActionPlan)
    assert result.steps[0].action == ActionName.CONVERT_UNIT
    assert result.steps[0].args["value"] == 5.0
    assert result.steps[0].args["from_unit"] == "L"
    assert result.steps[0].args["to_unit"] == "mL"


def test_add_two_numbers():
    result = parse_transcript("add 2 and 2")
    assert isinstance(result, ActionPlan)
    assert result.intent.name == IntentName.CALCULATOR_OPERATION
    assert result.steps[0].action == ActionName.ADD_CONSTANT
    assert result.steps[0].args["left"] == 2.0
    assert result.steps[0].args["right"] == 2.0


def test_greeting_is_not_command():
    result = parse_transcript("hello how are you")
    assert isinstance(result, ClarificationNeeded)
    assert result.status == ParseStatus.NOT_A_COMMAND


def test_empty_text_is_not_command():
    result = parse_transcript("   ")
    assert isinstance(result, ClarificationNeeded)
    assert result.status == ParseStatus.NOT_A_COMMAND


def test_write_journal_only_action_plan():
    result = parse_transcript("write to journal")
    assert isinstance(result, ActionPlan | NoteCapture)


def test_subtract_operation_from_slot():
    result = parse_transcript("take result from calculator 2, subtract 1")
    assert isinstance(result, ActionPlan)
    assert result.steps[0].action == ActionName.READ_CALCULATOR_RESULT
    assert result.steps[1].action == ActionName.SUBTRACT_CONSTANT
    assert result.steps[1].args["value_from"] == "s1"


def test_multiply_operation_from_slot():
    result = parse_transcript("take result from calculator 3 and multiply by 4")
    assert isinstance(result, ActionPlan)
    assert result.steps[1].action == ActionName.MULTIPLY_CONSTANT


def test_divide_operation_from_slot():
    result = parse_transcript("take result from calculator 4 and divide by 2")
    assert isinstance(result, ActionPlan)
    assert result.steps[1].action == ActionName.DIVIDE_CONSTANT


def test_slot_extraction():
    result = parse_transcript("read calculator 9 then add 2")
    assert isinstance(result, ActionPlan)
    assert result.entities.calculator_slot == 9


def test_unit_normalization_ml_to_l():
    result = parse_transcript("convert 10 ml to liters")
    assert isinstance(result, ActionPlan)
    step = result.steps[0]
    assert step.args["from_unit"] == "mL"
    assert step.args["to_unit"] == "L"


def test_not_supported_text():
    result = parse_transcript("please reboot the cluster rack")
    assert isinstance(result, ClarificationNeeded)
    assert result.status == ParseStatus.UNSUPPORTED


def test_protocol_case_insensitive():
    result = parse_transcript("Find protocol for western blot wash")
    assert isinstance(result, ActionPlan)
    assert result.intent.name == IntentName.RETRIEVE_PROTOCOL


def test_observation_keyword_turned():
    result = parse_transcript("the solution turned blue")
    assert isinstance(result, NoteCapture)
    assert result.note.content == "the solution turned blue"


def test_json_serializable_output():
    result = parse_transcript("convert 5 liters to milliliters")
    payload = result.model_dump()
    assert isinstance(payload, dict)
    assert payload["kind"] == ResultKind.ACTION_PLAN


def test_step_ids_are_stable_sequence():
    result = parse_transcript(
        "take result from calculator 1, add 2, convert liters to mL, write to journal"
    )
    assert isinstance(result, ActionPlan)
    assert [s.step_id for s in result.steps] == ["s1", "s2", "s3", "s4"]


def test_calculate_sinus_is_unsupported():
    result = parse_transcript("calculate sinus of 30 degrees")
    assert isinstance(result, ClarificationNeeded)
    assert result.status == ParseStatus.UNSUPPORTED


def test_create_3d_simulation_is_unsupported():
    result = parse_transcript("create a 3d simulation")
    assert isinstance(result, ClarificationNeeded)
    assert result.status == ParseStatus.UNSUPPORTED


def test_plot_result_is_unsupported():
    result = parse_transcript("plot this result")
    assert isinstance(result, ClarificationNeeded)
    assert result.status == ParseStatus.UNSUPPORTED


def test_thanks_is_not_a_command():
    result = parse_transcript("thanks for your help")
    assert isinstance(result, ClarificationNeeded)
    assert result.status == ParseStatus.NOT_A_COMMAND


def test_clarification_needed_is_never_ready():
    result = parse_transcript("take the previous value and write it down")
    assert isinstance(result, ClarificationNeeded)
    assert result.status != ParseStatus.READY
