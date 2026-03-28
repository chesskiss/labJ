"""Executor-only examples using direct module inputs (no parser/validator calls)."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `uv run python examples.py` from inside executor_runtime/.
if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from context_action_plan.enums import ActionName, IntentName, ResultKind
from context_action_plan.schemas import ActionPlan, ActionStep, EntityBundle, IntentInfo
from plan_validation.schemas import ValidationResult

try:
    from .executor import execute_validated_output
    from .mock_state import MockRuntime
except ImportError:  # direct script execution
    from executor_runtime.executor import execute_validated_output
    from executor_runtime.mock_state import MockRuntime


def _example_action_plan() -> ActionPlan:
    """Build a validated-style ActionPlan input directly for executor testing."""
    return ActionPlan(
        user_text="take result from calculator 1, add 2, convert liters to mL, write to journal",
        intent=IntentInfo(name=IntentName.TRANSFORM_AND_RECORD_VALUE, confidence=0.94),
        entities=EntityBundle(
            calculator_slot=1, operand=2.0, source_unit="L", target_unit="mL"
        ),
        steps=[
            ActionStep(
                step_id="s1", action=ActionName.READ_CALCULATOR_RESULT, args={"slot": 1}
            ),
            ActionStep(
                step_id="s2",
                action=ActionName.ADD_CONSTANT,
                args={"value_from": "s1", "operand": 2.0},
            ),
            ActionStep(
                step_id="s3",
                action=ActionName.CONVERT_UNIT,
                args={"value_from": "s2", "from_unit": "L", "to_unit": "mL"},
            ),
            ActionStep(
                step_id="s4",
                action=ActionName.WRITE_JOURNAL_ENTRY,
                args={"content_mode": "auto_from_previous_steps", "value_from": "s3"},
            ),
        ],
    )


def _example_validation_result() -> ValidationResult:
    """Build a validation input directly for executor testing."""
    return ValidationResult(
        is_valid=True,
        is_executable=True,
        normalized_kind=ResultKind.ACTION_PLAN,
        errors=[],
        warnings=[],
    )


def run_examples() -> list[dict]:
    """Run executor examples using direct inputs expected by the executor contract."""
    runtime = MockRuntime(
        active_session_exists=True,
        calculator_slots={1: {"value": 3.5, "unit": "L"}},
        protocol_index={
            "pcr cleanup": {"title": "PCR Cleanup", "content": "Step 1 ..."}
        },
    )

    parsed = _example_action_plan()
    validation = _example_validation_result()
    result = execute_validated_output(
        parsed=parsed, validation=validation, runtime=runtime
    )

    return [
        {
            "parsed_input": parsed.model_dump(mode="json"),
            "validation_input": validation.model_dump(mode="json"),
            "execution_output": result.model_dump(mode="json"),
        }
    ]


if __name__ == "__main__":
    for row in run_examples():
        print(row)
