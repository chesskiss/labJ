"""Factory helpers for deterministic mock runtime state creation."""

from __future__ import annotations

from .schemas import (
    CalculatorSlotValue,
    MockRuntimeState,
    ProtocolRecord,
    RecentResult,
)


def make_empty_runtime() -> MockRuntimeState:
    """Create an empty baseline runtime state."""
    return MockRuntimeState()


def make_runtime_with_active_session(
    session_id: str = "session_001",
    title: str = "Untitled Session",
    runtime: MockRuntimeState | None = None,
) -> MockRuntimeState:
    """Create or update runtime with an active session."""
    state = _clone_or_empty(runtime)
    state.active_session_exists = True
    state.active_session_id = session_id
    state.active_session_title = title
    if session_id not in state.open_sessions:
        state.open_sessions.append(session_id)
    return state


def make_runtime_with_calculator(
    slot: int = 1,
    value: float = 3.5,
    unit: str = "L",
    runtime: MockRuntimeState | None = None,
) -> MockRuntimeState:
    """Create or update runtime with a calculator slot value."""
    state = _clone_or_empty(runtime)
    state.calculator_slots[slot] = CalculatorSlotValue(value=float(value), unit=unit)
    return state


def make_runtime_with_protocol(
    name: str = "pcr cleanup",
    title: str = "PCR Cleanup",
    content: str = "Step 1 ...",
    runtime: MockRuntimeState | None = None,
) -> MockRuntimeState:
    """Create or update runtime with a protocol record."""
    state = _clone_or_empty(runtime)
    state.protocol_index[name.strip().lower()] = ProtocolRecord(
        title=title, content=content
    )
    return state


def make_runtime_with_context_summary(
    summary: str = "Active session summary",
    runtime: MockRuntimeState | None = None,
) -> MockRuntimeState:
    """Create or update runtime with compact context summary fields."""
    state = _clone_or_empty(runtime)
    state.session_context_summary = summary
    if not state.recent_results:
        state.recent_results.append(
            RecentResult(label="calculator_1_latest", value=3.5, unit="L")
        )
    if not state.recent_entities:
        state.recent_entities = {
            "last_protocol": "pcr cleanup",
            "session_state": "active",
        }
    return state


def make_demo_runtime() -> MockRuntimeState:
    """Create a deterministic demo runtime combining the common helper states."""
    state = make_runtime_with_active_session(session_id="session_001", title="PCR run")
    state = make_runtime_with_calculator(slot=1, value=3.5, unit="L", runtime=state)
    state = make_runtime_with_calculator(slot=2, value=10.0, unit="mL", runtime=state)
    state = make_runtime_with_protocol(
        name="pcr cleanup",
        title="PCR Cleanup",
        content="Step 1: bind. Step 2: wash. Step 3: elute.",
        runtime=state,
    )
    state = make_runtime_with_context_summary(
        summary="Active session: PCR run. Latest calculator result: 3.5 L in slot 1.",
        runtime=state,
    )
    return state


def _clone_or_empty(runtime: MockRuntimeState | None) -> MockRuntimeState:
    if runtime is None:
        return make_empty_runtime()
    return runtime.model_copy(deep=True)
