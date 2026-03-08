"""Example validation scenarios."""

from context_action_plan.parser import parse_transcript

from .validator import validate_parsed_output


def demo_validation() -> dict:
    """Return a sample validation result for demo/debug usage."""
    parsed = parse_transcript(
        "take result from calculator 1, add 2, convert liters to mL, write to journal"
    )
    return validate_parsed_output(parsed).model_dump()


print(demo_validation())
