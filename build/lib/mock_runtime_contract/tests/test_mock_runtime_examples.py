from mock_runtime_contract.examples import get_example_states


def test_examples_return_expected_items():
    items = get_example_states()
    assert len(items) == 5
    names = {item["name"] for item in items}
    assert names == {
        "empty_runtime",
        "active_with_calculator",
        "with_protocol",
        "with_context_summary",
        "demo_runtime",
    }


def test_demo_runtime_example_has_summary_and_results():
    demo = next(item for item in get_example_states() if item["name"] == "demo_runtime")
    state = demo["state"]
    assert state["active_session_exists"] is True
    assert state["session_context_summary"]
    assert state["recent_results"]
