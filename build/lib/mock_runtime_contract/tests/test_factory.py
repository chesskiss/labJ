from mock_runtime_contract.factory import (
    make_demo_runtime,
    make_empty_runtime,
    make_runtime_with_active_session,
    make_runtime_with_calculator,
    make_runtime_with_context_summary,
    make_runtime_with_protocol,
)


def test_make_empty_runtime():
    state = make_empty_runtime()
    assert state.active_session_exists is False
    assert not state.calculator_slots


def test_make_runtime_with_active_session():
    state = make_runtime_with_active_session(session_id="session_abc", title="PCR Run")
    assert state.active_session_exists is True
    assert state.active_session_id == "session_abc"
    assert state.active_session_title == "PCR Run"
    assert "session_abc" in state.open_sessions


def test_make_runtime_with_calculator():
    state = make_runtime_with_calculator(slot=3, value=8.2, unit="mL")
    assert state.calculator_slots[3].value == 8.2
    assert state.calculator_slots[3].unit == "mL"


def test_make_runtime_with_protocol():
    state = make_runtime_with_protocol(
        name="pcr cleanup", title="PCR Cleanup", content="Step 1 ..."
    )
    assert "pcr cleanup" in state.protocol_index
    assert state.protocol_index["pcr cleanup"].title == "PCR Cleanup"


def test_make_runtime_with_context_summary():
    state = make_runtime_with_context_summary(summary="Session summary")
    assert state.session_context_summary == "Session summary"
    assert state.recent_results
    assert state.recent_entities


def test_factories_are_composable_without_mutating_previous():
    s1 = make_runtime_with_active_session(session_id="session_001")
    s2 = make_runtime_with_calculator(slot=1, value=3.5, unit="L", runtime=s1)
    assert 1 not in s1.calculator_slots
    assert 1 in s2.calculator_slots


def test_make_demo_runtime_contents():
    state = make_demo_runtime()
    assert state.active_session_exists is True
    assert state.active_session_id == "session_001"
    assert 1 in state.calculator_slots
    assert 2 in state.calculator_slots
    assert "pcr cleanup" in state.protocol_index
    assert state.session_context_summary is not None
    assert state.recent_results
