import os

from fastapi.testclient import TestClient

from context_action_plan.llm_parser import reset_default_llm_parser_for_tests
from orchestration_api.app import app
from orchestration_api.runtime import reset_runtime_for_tests


def test_health_ok():
    os.environ.pop("LLM_API_KEY", None)
    os.environ.pop("GROQ_API_KEY", None)
    reset_default_llm_parser_for_tests()
    reset_runtime_for_tests()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "orchestration_api"
    assert payload["components"]["parser_loaded"] is True
    assert payload["components"]["llm_parser_configured"] is False
    assert payload["components"]["validator_loaded"] is True
    assert payload["components"]["executor_loaded"] is True
    assert payload["components"]["journal_tool_configured"] is True
