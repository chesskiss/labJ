"""LLM-backed parser with deterministic fallback."""

from __future__ import annotations

import json
import os
from typing import Any

from pydantic import TypeAdapter

from .enums import IntentName, NoteType, ParseStatus, ResultKind
from .parser import parse_transcript
from .schemas import ParsedOutput

DEFAULT_LLM_MODEL = "llama-3.3-70b-versatile"
DEFAULT_LLM_BASE_URL = "https://api.groq.com/openai/v1"

_PARSED_OUTPUT_ADAPTER = TypeAdapter(ParsedOutput)
_DEFAULT_LLM_PARSER: "LLMTranscriptParser | None" = None


class LLMTranscriptParser:
    """Wrapper around OpenAI-compatible chat completions returning ParsedOutput."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 20.0,
        client: Any | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY")
        self.model = model or os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL)
        self.base_url = base_url or os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL)
        self.timeout_seconds = timeout_seconds
        self._client = client
        self.is_configured = bool(self.api_key)

        if self._client is None and self.is_configured:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout_seconds,
            )

    def parse(self, text: str) -> ParsedOutput:
        """Parse text through LLM and validate against ParsedOutput schema."""
        if not self.is_configured or self._client is None:
            raise RuntimeError("LLM parser is not configured")

        print(
            f"[LLM] calling chat.completions model={self.model} base_url={self.base_url}"
        )
        completion = self._client.chat.completions.create(
            model=self.model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": text},
            ],
        )
        print("[LLM] response received")

        content = completion.choices[0].message.content
        if not content:
            raise ValueError("LLM returned empty content")
        print(f"[LLM] response content length={len(content)}")
        print(f"[LLM] raw content={content}")

        parsed = json.loads(content)
        parsed = _normalize_llm_payload(parsed, text)
        model = _PARSED_OUTPUT_ADAPTER.validate_python(parsed)
        if (
            model.status == ParseStatus.READY
            and model.kind.value == "clarification_needed"
        ):
            raise ValueError("Invalid model combination returned by LLM")
        print("[LLM] parse success")
        return model


def parse_transcript_with_fallback(
    text: str, llm_parser: LLMTranscriptParser | None = None
) -> ParsedOutput:
    """Try LLM parsing; always fallback to deterministic parser on any failure."""
    parser = llm_parser or get_default_llm_parser()
    print(f"[LLM] parser configured={parser.is_configured}")
    if parser.is_configured:
        try:
            return parser.parse(text)
        except Exception as exc:
            print(
                "[LLM] parse failed; falling back to deterministic parser: "
                f"{type(exc).__name__}: {exc}"
            )
            return parse_transcript(text)
    print("[LLM] parser not configured; using deterministic parser")
    return parse_transcript(text)


def get_default_llm_parser() -> LLMTranscriptParser:
    """Return process-wide LLM parser singleton."""
    global _DEFAULT_LLM_PARSER
    if _DEFAULT_LLM_PARSER is None:
        _DEFAULT_LLM_PARSER = LLMTranscriptParser()
    return _DEFAULT_LLM_PARSER


def reset_default_llm_parser_for_tests() -> None:
    """Reset singleton LLM parser (test helper)."""
    global _DEFAULT_LLM_PARSER
    _DEFAULT_LLM_PARSER = None


def _system_prompt() -> str:
    return (
        "Convert user transcript text into exactly one JSON object matching this contract: "
        "kind in {action_plan,note_capture,clarification_needed}; status in "
        "{ready,needs_clarification,recognized_but_unimplemented,not_a_command,unsupported}. "
        "For executable requests emit action_plan with explicit steps using supported actions: "
        "read_calculator_result, add_constant, subtract_constant, multiply_constant, "
        "divide_constant, convert_unit, write_journal_entry, search_protocol, record_observation. "
        "For observational notes emit note_capture. "
        "For missing info emit clarification_needed+needs_clarification. "
        "For conversational text emit clarification_needed+not_a_command. "
        "For unknown tasks emit clarification_needed+unsupported. "
        "Return valid JSON only, no markdown."
    )


def _normalize_llm_payload(payload: Any, user_text: str) -> dict[str, Any]:
    """Normalize imperfect LLM JSON into ParsedOutput-compatible shape."""
    if not isinstance(payload, dict):
        raise ValueError("LLM payload must be a JSON object")

    normalized: dict[str, Any] = dict(payload)
    kind = str(normalized.get("kind") or ResultKind.CLARIFICATION_NEEDED.value)
    if kind not in {
        ResultKind.ACTION_PLAN.value,
        ResultKind.NOTE_CAPTURE.value,
        ResultKind.CLARIFICATION_NEEDED.value,
    }:
        kind = ResultKind.CLARIFICATION_NEEDED.value

    normalized["kind"] = kind
    normalized.setdefault("user_text", user_text)
    normalized.setdefault("scope", {"session": "active", "session_ref": None})
    normalized.setdefault(
        "entities",
        {
            "source_kind": None,
            "source_ref": None,
            "source_index": None,
            "calculator_slot": None,
            "operand": None,
            "source_unit": None,
            "target_unit": None,
            "protocol_name": None,
            "free_text_value": user_text,
        },
    )
    normalized.setdefault("missing", [])
    normalized.setdefault("ambiguities", [])
    normalized.setdefault("steps", [])
    normalized.setdefault("notes", [])

    if kind == ResultKind.NOTE_CAPTURE.value:
        normalized.setdefault("status", ParseStatus.READY.value)
        note = normalized.get("note")
        if isinstance(note, str):
            normalized["note"] = {
                "note_type": NoteType.OBSERVATION.value,
                "content": note,
            }
        elif isinstance(note, dict):
            note.setdefault("note_type", NoteType.OBSERVATION.value)
            note.setdefault("content", user_text)
        else:
            normalized["note"] = {
                "note_type": NoteType.OBSERVATION.value,
                "content": user_text,
            }
        normalized.setdefault(
            "intent",
            {"name": IntentName.RECORD_OBSERVATION.value, "confidence": 0.9},
        )
        return normalized

    if kind == ResultKind.ACTION_PLAN.value:
        normalized.setdefault("status", ParseStatus.READY.value)
        normalized.setdefault(
            "intent",
            {"name": IntentName.CALCULATOR_OPERATION.value, "confidence": 0.8},
        )
        return normalized

    status = normalized.get("status") or ParseStatus.UNSUPPORTED.value
    if status not in {
        ParseStatus.NEEDS_CLARIFICATION.value,
        ParseStatus.RECOGNIZED_BUT_UNIMPLEMENTED.value,
        ParseStatus.NOT_A_COMMAND.value,
        ParseStatus.UNSUPPORTED.value,
    }:
        status = ParseStatus.UNSUPPORTED.value
    normalized["status"] = status
    normalized.setdefault(
        "intent",
        {"name": IntentName.UNSUPPORTED.value, "confidence": 0.5},
    )
    return normalized
