"""Example runtime states for local debugging and tests."""

from __future__ import annotations

from .factory import (
    make_demo_runtime,
    make_empty_runtime,
    make_runtime_with_active_session,
    make_runtime_with_calculator,
    make_runtime_with_context_summary,
    make_runtime_with_protocol,
)


def get_example_states() -> list[dict]:
    """Return serialized example runtime states."""
    empty = make_empty_runtime()
    with_session_and_calc = make_runtime_with_calculator(
        slot=1,
        value=3.5,
        unit="L",
        runtime=make_runtime_with_active_session(
            session_id="session_001", title="PCR run"
        ),
    )
    with_protocol = make_runtime_with_protocol(
        name="pcr cleanup",
        title="PCR Cleanup",
        content="Step 1 ...",
        runtime=with_session_and_calc,
    )
    with_summary = make_runtime_with_context_summary(
        summary="Active session: PCR run. Latest calculator result: 3.5 L in slot 1.",
        runtime=with_protocol,
    )
    demo = make_demo_runtime()

    return [
        {"name": "empty_runtime", "state": empty.model_dump(mode="json")},
        {
            "name": "active_with_calculator",
            "state": with_session_and_calc.model_dump(mode="json"),
        },
        {"name": "with_protocol", "state": with_protocol.model_dump(mode="json")},
        {"name": "with_context_summary", "state": with_summary.model_dump(mode="json")},
        {"name": "demo_runtime", "state": demo.model_dump(mode="json")},
    ]


if __name__ == "__main__":
    for item in get_example_states():
        print(item["name"], item["state"])
