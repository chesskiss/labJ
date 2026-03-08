from executor_runtime.resolver import resolve_step_args


def test_resolve_value_from_success():
    args = {"value_from": "s1", "operand": 2}
    step_results = {"s1": {"value": 3.5, "unit": "L"}}

    resolved, err = resolve_step_args(args, step_results)

    assert err is None
    assert resolved is not None
    assert resolved["resolved_value"] == 3.5
    assert resolved["resolved_unit"] == "L"


def test_resolve_value_from_missing_step():
    resolved, err = resolve_step_args({"value_from": "s2"}, {"s1": {"value": 1}})

    assert resolved is None
    assert err is not None
    assert err.code.value == "INVALID_REFERENCE_RESOLUTION"


def test_resolve_value_from_wrong_type():
    resolved, err = resolve_step_args({"value_from": 12}, {})

    assert resolved is None
    assert err is not None
    assert err.code.value == "INVALID_REFERENCE_RESOLUTION"


def test_resolve_no_reference_passthrough():
    args = {"value": 5, "from_unit": "L", "to_unit": "mL"}
    resolved, err = resolve_step_args(args, {})

    assert err is None
    assert resolved == args
