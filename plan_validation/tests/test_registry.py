"""Registry contract tests."""

from context_action_plan.enums import ActionName

from plan_validation.registry import build_default_registry


def test_registry_contains_required_actions():
    registry = build_default_registry()
    expected = {
        ActionName.READ_CALCULATOR_RESULT,
        ActionName.ADD_CONSTANT,
        ActionName.SUBTRACT_CONSTANT,
        ActionName.MULTIPLY_CONSTANT,
        ActionName.DIVIDE_CONSTANT,
        ActionName.CONVERT_UNIT,
        ActionName.WRITE_JOURNAL_ENTRY,
        ActionName.SEARCH_PROTOCOL,
        ActionName.RECORD_OBSERVATION,
    }
    assert set(registry.actions()) == expected


def test_convert_unit_contract_has_units_and_one_of_value_sources():
    registry = build_default_registry()
    spec = registry.get(ActionName.CONVERT_UNIT)
    assert spec is not None
    req = {arg.name for arg in spec.required_args}
    assert {"from_unit", "to_unit"} <= req
    assert ["value", "value_from"] in spec.one_of


def test_add_constant_contract_supports_both_shapes():
    registry = build_default_registry()
    spec = registry.get(ActionName.ADD_CONSTANT)
    assert spec is not None
    optional = {arg.name for arg in spec.optional_args}
    assert {"value_from", "operand", "left", "right"} <= optional


def test_registry_has_known_unimplemented_capabilities():
    registry = build_default_registry()
    assert "trigonometric_calculation" in registry.known_unimplemented_capabilities
    assert "plotting" in registry.known_unimplemented_capabilities
    assert "simulation" in registry.known_unimplemented_capabilities
