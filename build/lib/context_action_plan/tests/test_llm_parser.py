"""Tests for LLM parser wrapper and fallback behavior."""

from __future__ import annotations

from context_action_plan.enums import ParseStatus, ResultKind
from context_action_plan.llm_parser import (
    LLMTranscriptParser,
    parse_transcript_with_fallback,
)


class _FakeCompletions:
    def __init__(self, content: str):
        self._content = content

    def create(self, **kwargs):  # noqa: ANN003
        del kwargs
        message = type("Message", (), {"content": self._content})
        choice = type("Choice", (), {"message": message})
        return type("Completion", (), {"choices": [choice]})


class _FakeClient:
    def __init__(self, content: str):
        self.chat = type(
            "Chat",
            (),
            {"completions": _FakeCompletions(content)},
        )


def test_llm_parse_success_with_fake_client():
    parser = LLMTranscriptParser(
        api_key="test-key",
        client=_FakeClient(
            '{"kind":"note_capture","status":"ready","user_text":"sample 4 became cloudy after heating","scope":{"session":"active","session_ref":null},"intent":{"name":"record_observation","confidence":0.95},"note":{"note_type":"observation","content":"sample 4 became cloudy after heating"},"entities":{"free_text_value":"sample 4 became cloudy after heating"},"missing":[],"ambiguities":[],"steps":[],"notes":[]}'
        ),
    )
    result = parser.parse("sample 4 became cloudy after heating")
    assert result.kind == ResultKind.NOTE_CAPTURE
    assert result.status == ParseStatus.READY


def test_parse_with_fallback_when_llm_not_configured():
    parser = LLMTranscriptParser(api_key=None, client=None)
    result = parse_transcript_with_fallback("hello how are you", llm_parser=parser)
    assert result.kind == ResultKind.CLARIFICATION_NEEDED
    assert result.status == ParseStatus.NOT_A_COMMAND


def test_parse_with_fallback_when_llm_raises():
    class _FailingParser:
        is_configured = True

        def parse(self, text: str):  # noqa: ANN001
            del text
            raise RuntimeError("connection refused")

    result = parse_transcript_with_fallback(
        "sample 4 became cloudy after heating",
        llm_parser=_FailingParser(),  # type: ignore[arg-type]
    )
    assert result.kind == ResultKind.NOTE_CAPTURE
    assert result.status == ParseStatus.READY


def test_llm_note_capture_string_payload_is_normalized():
    parser = LLMTranscriptParser(
        api_key="test-key",
        client=_FakeClient(
            '{"kind":"note_capture","note":"Sample 4 is now clearer and more viscous due to cooling"}'
        ),
    )
    result = parser.parse("sample 4 due to cooling is now clearer and viscous")
    assert result.kind == ResultKind.NOTE_CAPTURE
    assert (
        result.note.content == "Sample 4 is now clearer and more viscous due to cooling"
    )
    assert result.user_text == "sample 4 due to cooling is now clearer and viscous"


def test_llm_unknown_kind_is_normalized_to_unsupported():
    parser = LLMTranscriptParser(
        api_key="test-key",
        client=_FakeClient('{"kind":"something_else","note":"x"}'),
    )
    result = parser.parse("do something else")
    assert result.kind == ResultKind.CLARIFICATION_NEEDED
    assert result.status == ParseStatus.UNSUPPORTED


def test_llm_clarification_salvages_note_capture_from_mixed_input():
    parser = LLMTranscriptParser(
        api_key="test-key",
        client=_FakeClient(
            '{"kind":"clarification_needed","status":"needs_clarification","user_text":"mixed"}'
        ),
    )
    result = parse_transcript_with_fallback(
        "sample 4 became cloudy after heating. take the previous value and write it down",
        llm_parser=parser,
    )
    assert result.kind == ResultKind.NOTE_CAPTURE
    assert "sample 4 became cloudy after heating" in result.note.content
