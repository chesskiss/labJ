"""Default tool registry for action plan validation."""

from context_action_plan.enums import ActionName

from .enums import ToolCategory, ValueKind
from .schemas import ArgSpec, ToolRegistry, ToolSpec


def build_default_registry() -> ToolRegistry:
    """Build the default approved tool registry contract."""
    tools: dict[ActionName, ToolSpec] = {
        ActionName.READ_CALCULATOR_RESULT: ToolSpec(
            name=ActionName.READ_CALCULATOR_RESULT,
            description="Read latest result from a calculator slot.",
            category=ToolCategory.READ,
            required_args=[ArgSpec(name="slot", kind=ValueKind.INT)],
            allow_step_references=False,
        ),
        ActionName.ADD_CONSTANT: ToolSpec(
            name=ActionName.ADD_CONSTANT,
            description="Add a constant to an existing value or add two literals.",
            category=ToolCategory.COMPUTE,
            optional_args=[
                ArgSpec(name="value_from", kind=ValueKind.STEP_REF),
                ArgSpec(name="operand", kind=ValueKind.NUMBER),
                ArgSpec(name="left", kind=ValueKind.NUMBER),
                ArgSpec(name="right", kind=ValueKind.NUMBER),
            ],
            one_of=[["value_from", "left"]],
        ),
        ActionName.SUBTRACT_CONSTANT: ToolSpec(
            name=ActionName.SUBTRACT_CONSTANT,
            description="Subtract constant from prior value.",
            category=ToolCategory.COMPUTE,
            required_args=[
                ArgSpec(name="value_from", kind=ValueKind.STEP_REF),
                ArgSpec(name="operand", kind=ValueKind.NUMBER),
            ],
        ),
        ActionName.MULTIPLY_CONSTANT: ToolSpec(
            name=ActionName.MULTIPLY_CONSTANT,
            description="Multiply prior value by constant.",
            category=ToolCategory.COMPUTE,
            required_args=[
                ArgSpec(name="value_from", kind=ValueKind.STEP_REF),
                ArgSpec(name="operand", kind=ValueKind.NUMBER),
            ],
        ),
        ActionName.DIVIDE_CONSTANT: ToolSpec(
            name=ActionName.DIVIDE_CONSTANT,
            description="Divide prior value by constant.",
            category=ToolCategory.COMPUTE,
            required_args=[
                ArgSpec(name="value_from", kind=ValueKind.STEP_REF),
                ArgSpec(name="operand", kind=ValueKind.NUMBER),
            ],
        ),
        ActionName.CONVERT_UNIT: ToolSpec(
            name=ActionName.CONVERT_UNIT,
            description="Convert value from one unit to another.",
            category=ToolCategory.COMPUTE,
            required_args=[
                ArgSpec(name="from_unit", kind=ValueKind.STR),
                ArgSpec(name="to_unit", kind=ValueKind.STR),
            ],
            optional_args=[
                ArgSpec(name="value", kind=ValueKind.NUMBER),
                ArgSpec(name="value_from", kind=ValueKind.STEP_REF),
            ],
            one_of=[["value", "value_from"]],
        ),
        ActionName.WRITE_JOURNAL_ENTRY: ToolSpec(
            name=ActionName.WRITE_JOURNAL_ENTRY,
            description="Write a journal entry from literal content or prior step output.",
            category=ToolCategory.WRITE,
            optional_args=[
                ArgSpec(name="content_mode", kind=ValueKind.STR),
                ArgSpec(name="content", kind=ValueKind.STR),
                ArgSpec(name="value_from", kind=ValueKind.STEP_REF),
            ],
            one_of=[["content", "content_mode"]],
        ),
        ActionName.SEARCH_PROTOCOL: ToolSpec(
            name=ActionName.SEARCH_PROTOCOL,
            description="Search protocol by name or query.",
            category=ToolCategory.SEARCH,
            required_args=[ArgSpec(name="protocol_name", kind=ValueKind.STR)],
            allow_step_references=False,
        ),
        ActionName.RECORD_OBSERVATION: ToolSpec(
            name=ActionName.RECORD_OBSERVATION,
            description="Record observation text.",
            category=ToolCategory.WRITE,
            required_args=[ArgSpec(name="content", kind=ValueKind.STR)],
            allow_step_references=False,
        ),
    }
    known_unimplemented_capabilities = [
        "trigonometric_calculation",
        "plotting",
        "simulation",
    ]
    return ToolRegistry(
        tools=tools,
        known_unimplemented_capabilities=known_unimplemented_capabilities,
    )
