"""Argument reference resolution for execution steps."""

from __future__ import annotations

from typing import Any

from .enums import RuntimeErrorCode
from .schemas import RuntimeErrorInfo


def resolve_step_args(
    args: dict[str, Any],
    step_results: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any] | None, RuntimeErrorInfo | None]:
    """Resolve args that reference prior step outputs.

    Supported reference forms:
    - value_from: "s1"  -> injects resolved value/unit into the current args.
    """
    resolved = dict(args)
    value_from = resolved.get("value_from")

    if value_from is None:
        return resolved, None

    if not isinstance(value_from, str):
        return None, RuntimeErrorInfo(
            code=RuntimeErrorCode.INVALID_REFERENCE_RESOLUTION,
            message="value_from must be a step_id string",
        )

    source = step_results.get(value_from)
    if source is None:
        return None, RuntimeErrorInfo(
            code=RuntimeErrorCode.INVALID_REFERENCE_RESOLUTION,
            message=f"referenced step {value_from} is missing from previous outputs",
        )

    # Keep traceable source reference and expose concrete numeric value for tools.
    if "resolved_from_step" not in resolved:
        resolved["resolved_from_step"] = value_from

    if "value" in source and "value" not in resolved:
        resolved["resolved_value"] = source["value"]

    if "unit" in source and "resolved_unit" not in resolved:
        resolved["resolved_unit"] = source["unit"]

    return resolved, None
