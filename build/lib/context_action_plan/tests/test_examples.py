"""Tests for examples module."""

from context_action_plan.examples import EXAMPLE_INPUTS, get_example_outputs
from context_action_plan.schemas import ParsedOutput


def test_examples_count():
    assert len(EXAMPLE_INPUTS) == 8


def test_example_outputs_align_with_inputs():
    outputs = get_example_outputs()
    assert len(outputs) == len(EXAMPLE_INPUTS)


def test_example_outputs_are_serializable():
    outputs = get_example_outputs()
    for item in outputs:
        assert isinstance(item, ParsedOutput.__args__)  # type: ignore[attr-defined]
        dumped = item.model_dump()
        assert isinstance(dumped, dict)
        assert "kind" in dumped
