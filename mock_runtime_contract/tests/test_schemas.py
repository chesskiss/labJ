from mock_runtime_contract.schemas import (
    CalculatorSlotValue,
    MockRuntimeState,
    ObservationRecord,
    ProtocolRecord,
    RecentResult,
)


def test_mock_runtime_defaults_are_empty():
    state = MockRuntimeState()
    assert state.active_session_exists is False
    assert state.active_session_id is None
    assert state.calculator_slots == {}
    assert state.journal_entries == []
    assert state.protocol_index == {}
    assert state.observations == []
    assert state.recent_results == []


def test_calculator_slot_typing():
    state = MockRuntimeState(
        calculator_slots={1: CalculatorSlotValue(value=3.5, unit="L")}
    )
    assert state.calculator_slots[1].value == 3.5
    assert state.calculator_slots[1].unit == "L"


def test_protocol_index_typing():
    state = MockRuntimeState(
        protocol_index={
            "pcr cleanup": ProtocolRecord(title="PCR Cleanup", content="Step 1")
        }
    )
    assert state.protocol_index["pcr cleanup"].title == "PCR Cleanup"


def test_recent_results_structure():
    state = MockRuntimeState(
        recent_results=[RecentResult(label="calculator_1_latest", value=3.5, unit="L")]
    )
    assert state.recent_results[0].label == "calculator_1_latest"
    assert state.recent_results[0].value == 3.5
    assert state.recent_results[0].unit == "L"


def test_observation_record_shape():
    state = MockRuntimeState(
        observations=[ObservationRecord(observation_index=0, content="cloudy sample")]
    )
    assert state.observations[0].content == "cloudy sample"


def test_model_dump_serializable():
    state = MockRuntimeState(
        active_session_exists=True,
        active_session_id="session_001",
        calculator_slots={1: {"value": 3.5, "unit": "L"}},
    )
    dumped = state.model_dump(mode="json")
    assert dumped["active_session_id"] == "session_001"
    assert dumped["calculator_slots"]["1"]["value"] == 3.5
