"""Mock tool handlers used by the executor runtime."""

from __future__ import annotations

from typing import Any, Callable

from context_action_plan.enums import ActionName

from .enums import RuntimeErrorCode
from .mock_state import MockRuntime
from .schemas import RuntimeErrorInfo

ToolHandler = Callable[
    [dict[str, Any], MockRuntime], tuple[dict[str, Any] | None, RuntimeErrorInfo | None]
]


def get_tool_handler(action: ActionName) -> ToolHandler:
    """Return mock handler for a validated action name."""
    handlers: dict[ActionName, ToolHandler] = {
        ActionName.READ_CALCULATOR_RESULT: _read_calculator_result,
        ActionName.ADD_CONSTANT: _add_constant,
        ActionName.SUBTRACT_CONSTANT: _subtract_constant,
        ActionName.MULTIPLY_CONSTANT: _multiply_constant,
        ActionName.DIVIDE_CONSTANT: _divide_constant,
        ActionName.CONVERT_UNIT: _convert_unit,
        ActionName.WRITE_JOURNAL_ENTRY: _write_journal_entry,
        ActionName.SEARCH_PROTOCOL: _search_protocol,
        ActionName.RECORD_OBSERVATION: _record_observation,
    }
    return handlers[action]


def _read_calculator_result(args: dict[str, Any], runtime: MockRuntime):
    if not runtime.active_session_exists:
        return None, _err(
            RuntimeErrorCode.NO_ACTIVE_SESSION, "no active session for calculator read"
        )

    slot = args.get("slot")
    if not isinstance(slot, int):
        return None, _err(
            RuntimeErrorCode.TOOL_EXECUTION_ERROR,
            "read_calculator_result requires integer slot",
        )
    slot_data = runtime.calculator_slots.get(slot)
    if slot_data is None:
        return None, _err(
            RuntimeErrorCode.CALCULATOR_SLOT_NOT_FOUND,
            f"Calculator slot {slot} does not exist in runtime state",
        )

    return {
        "value": slot_data.get("value"),
        "unit": slot_data.get("unit"),
        "source": f"calculator_slot_{slot}",
    }, None


def _add_constant(args: dict[str, Any], runtime: MockRuntime):
    del runtime
    left = args.get("left")
    right = args.get("right")
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        result = float(left) + float(right)
        return {
            "value": result,
            "unit": None,
            "expression": f"{left} + {right}",
        }, None

    value, unit, err = _resolve_numeric_input(args)
    if err:
        return None, err
    if value is None:
        return None, _err(
            RuntimeErrorCode.INVALID_REFERENCE_RESOLUTION,
            "operation requires resolved value_from or direct left operand",
        )

    operand, operand_err = _as_float(args.get("operand"), "operand")
    if operand_err:
        return None, operand_err
    if operand is None:
        return None, _err(
            RuntimeErrorCode.TOOL_EXECUTION_ERROR, "operand must be numeric"
        )
    result = value + operand
    return {
        "value": result,
        "unit": unit,
        "expression": f"{value} + {operand}",
    }, None


def _subtract_constant(args: dict[str, Any], runtime: MockRuntime):
    del runtime
    value, unit, err = _resolve_numeric_input(args)
    if err:
        return None, err
    if value is None:
        return None, _err(
            RuntimeErrorCode.INVALID_REFERENCE_RESOLUTION,
            "operation requires resolved value_from or direct left operand",
        )

    operand, operand_err = _as_float(args.get("operand"), "operand")
    if operand_err:
        return None, operand_err
    if operand is None:
        return None, _err(
            RuntimeErrorCode.TOOL_EXECUTION_ERROR, "operand must be numeric"
        )
    result = value - operand
    return {
        "value": result,
        "unit": unit,
        "expression": f"{value} - {operand}",
    }, None


def _multiply_constant(args: dict[str, Any], runtime: MockRuntime):
    del runtime
    value, unit, err = _resolve_numeric_input(args)
    if err:
        return None, err
    if value is None:
        return None, _err(
            RuntimeErrorCode.INVALID_REFERENCE_RESOLUTION,
            "operation requires resolved value_from or direct left operand",
        )

    operand, operand_err = _as_float(args.get("operand"), "operand")
    if operand_err:
        return None, operand_err
    if operand is None:
        return None, _err(
            RuntimeErrorCode.TOOL_EXECUTION_ERROR, "operand must be numeric"
        )
    result = value * operand
    return {
        "value": result,
        "unit": unit,
        "expression": f"{value} * {operand}",
    }, None


def _divide_constant(args: dict[str, Any], runtime: MockRuntime):
    del runtime
    value, unit, err = _resolve_numeric_input(args)
    if err:
        return None, err
    if value is None:
        return None, _err(
            RuntimeErrorCode.INVALID_REFERENCE_RESOLUTION,
            "operation requires resolved value_from or direct left operand",
        )

    operand, operand_err = _as_float(args.get("operand"), "operand")
    if operand_err:
        return None, operand_err
    if operand is None:
        return None, _err(
            RuntimeErrorCode.TOOL_EXECUTION_ERROR, "operand must be numeric"
        )
    if operand == 0.0:
        return None, _err(
            RuntimeErrorCode.DIVISION_BY_ZERO, "division by zero is not allowed"
        )

    result = value / operand
    return {
        "value": result,
        "unit": unit,
        "expression": f"{value} / {operand}",
    }, None


def _convert_unit(args: dict[str, Any], runtime: MockRuntime):
    del runtime

    from_unit = _normalize_unit(args.get("from_unit"))
    to_unit = _normalize_unit(args.get("to_unit"))

    value = args.get("value")
    if value is None:
        value = args.get("resolved_value")

    if value is None:
        return None, _err(
            RuntimeErrorCode.INVALID_REFERENCE_RESOLUTION,
            "convert_unit requires value or resolvable value_from",
        )

    numeric_value, value_err = _as_float(value, "value")
    if value_err:
        return None, value_err
    if numeric_value is None:
        return None, _err(
            RuntimeErrorCode.TOOL_EXECUTION_ERROR, "value must be numeric"
        )

    converted, err = _convert_number(numeric_value, from_unit, to_unit)
    if err:
        return None, err

    return {
        "value": converted,
        "unit": to_unit,
        "expression": f"{value} {from_unit} -> {converted} {to_unit}",
    }, None


def _write_journal_entry(args: dict[str, Any], runtime: MockRuntime):
    if not runtime.active_session_exists:
        return None, _err(
            RuntimeErrorCode.NO_ACTIVE_SESSION, "no active session for journal write"
        )

    content = args.get("content")
    if content is None:
        mode = args.get("content_mode")
        if mode == "auto_from_previous_steps" and "resolved_value" in args:
            value = args.get("resolved_value")
            unit = args.get("resolved_unit")
            if unit:
                content = f"Computed value: {value} {unit}"
            else:
                content = f"Computed value: {value}"
        elif mode == "auto_from_previous_steps":
            content = "Computed value from previous step"

    if not isinstance(content, str) or not content.strip():
        return None, _err(
            RuntimeErrorCode.TOOL_EXECUTION_ERROR,
            "write_journal_entry requires non-empty content or auto content mode",
        )

    runtime.journal_entries.append(content)
    return {
        "entry_index": len(runtime.journal_entries) - 1,
        "content": content,
    }, None


def _search_protocol(args: dict[str, Any], runtime: MockRuntime):
    name = args.get("protocol_name")
    if not isinstance(name, str) or not name.strip():
        return None, _err(
            RuntimeErrorCode.TOOL_EXECUTION_ERROR,
            "search_protocol requires protocol_name",
        )

    lookup = name.strip().lower()
    item = runtime.protocol_index.get(lookup)
    if item is None:
        return None, _err(
            RuntimeErrorCode.PROTOCOL_NOT_FOUND, f"Protocol '{name}' not found"
        )

    return {
        "title": item.get("title", name),
        "content": item.get("content", ""),
    }, None


def _record_observation(args: dict[str, Any], runtime: MockRuntime):
    if not runtime.active_session_exists:
        return None, _err(
            RuntimeErrorCode.NO_ACTIVE_SESSION,
            "no active session for observation recording",
        )

    content = args.get("content")
    if not isinstance(content, str) or not content.strip():
        return None, _err(
            RuntimeErrorCode.TOOL_EXECUTION_ERROR, "record_observation requires content"
        )

    runtime.observations.append(content)
    return {
        "saved": True,
        "content": content,
        "observation_index": len(runtime.observations) - 1,
    }, None


def _resolve_numeric_input(
    args: dict[str, Any],
) -> tuple[float | None, str | None, RuntimeErrorInfo | None]:
    if "resolved_value" in args:
        value = args.get("resolved_value")
        if isinstance(value, (int, float)):
            unit = args.get("resolved_unit")
            return float(value), unit if isinstance(unit, str) else None, None

    left = args.get("left")
    if isinstance(left, (int, float)):
        return float(left), None, None

    return (
        None,
        None,
        _err(
            RuntimeErrorCode.INVALID_REFERENCE_RESOLUTION,
            "operation requires resolved value_from or direct left operand",
        ),
    )


def _as_float(
    raw_value: Any, field_name: str
) -> tuple[float | None, RuntimeErrorInfo | None]:
    if isinstance(raw_value, (int, float)):
        return float(raw_value), None
    return None, _err(
        RuntimeErrorCode.TOOL_EXECUTION_ERROR,
        f"{field_name} must be numeric",
    )


def _normalize_unit(unit: Any) -> str:
    if not isinstance(unit, str):
        return ""

    val = unit.strip().lower()
    mapping = {
        "l": "L",
        "liter": "L",
        "liters": "L",
        "ml": "mL",
        "milliliter": "mL",
        "milliliters": "mL",
    }
    return mapping.get(val, unit.strip())


def _convert_number(
    value: float, from_unit: str, to_unit: str
) -> tuple[float | None, RuntimeErrorInfo | None]:
    if from_unit == to_unit:
        return value, None

    conversions = {
        ("L", "mL"): lambda x: x * 1000.0,
        ("mL", "L"): lambda x: x / 1000.0,
    }

    converter = conversions.get((from_unit, to_unit))
    if converter is None:
        return None, _err(
            RuntimeErrorCode.UNSUPPORTED_UNIT_CONVERSION,
            f"unsupported conversion from {from_unit} to {to_unit}",
        )

    return converter(value), None


def _err(code: RuntimeErrorCode, message: str) -> RuntimeErrorInfo:
    return RuntimeErrorInfo(code=code, message=message)
