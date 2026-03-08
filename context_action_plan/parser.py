"""Deterministic transcript -> ParsedOutput parser."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .enums import ActionName, IntentName, NoteType, ParseStatus
from .schemas import (
    ActionPlan,
    ActionStep,
    Ambiguity,
    ClarificationNeeded,
    EntityBundle,
    IntentInfo,
    MissingField,
    NoteCapture,
    NotePayload,
    ParsedOutput,
    ScopeInfo,
)

_GREETING_WORDS = {
    "hi",
    "hello",
    "hey",
    "good morning",
    "good afternoon",
    "how are you",
}

_OBSERVATION_HINTS = {
    "became",
    "observed",
    "after heating",
    "after mixing",
    "turned",
    "cloudy",
    "precipitate",
    "color changed",
}

_WRITE_HINTS = {"write down", "write it down", "record", "journal", "log"}
_CONVERSATIONAL_HINTS = {"thanks", "thank you"}

_UNIT_ALIASES = {
    "liter": "L",
    "liters": "L",
    "l": "L",
    "milliliter": "mL",
    "milliliters": "mL",
    "ml": "mL",
    "mL": "mL",
    "ul": "uL",
    "microliter": "uL",
    "microliters": "uL",
}


@dataclass
class _StepBuilder:
    """Helper for generating stable step ids."""

    index: int = 0

    def next_id(self) -> str:
        self.index += 1
        return f"s{self.index}"


def parse_transcript(text: str) -> ParsedOutput:
    """Parse free-text transcript into a stable structured contract."""
    user_text = (text or "").strip()
    if not user_text:
        return _not_a_command("", "empty input")

    lowered = user_text.lower().strip()

    if _is_conversational(lowered):
        return _not_a_command(user_text, "greeting or conversational text")

    intent_family = _determine_intent_family(user_text)
    if intent_family is None:
        return _unsupported(user_text)

    protocol = _extract_protocol_query(user_text)
    if protocol:
        return _build_protocol_plan(user_text, protocol)

    if _is_ambiguous_previous_value(lowered):
        return _build_previous_value_clarification(user_text)

    plan = _build_action_plan(user_text)
    if plan is not None:
        return plan

    note_capture = _build_note_capture(user_text)
    if note_capture is not None:
        return note_capture

    return _unsupported(user_text)


def _build_action_plan(user_text: str) -> Optional[ActionPlan]:
    lowered = user_text.lower()
    if re.search(r"(write down|record|log)\s+result\s+[0-9]+(?:\.[0-9]+)?", lowered):
        # Keep explicit "write down result ..." flows as NoteCapture.
        return None

    entities = EntityBundle()
    steps: list[ActionStep] = []
    sb = _StepBuilder()
    prev_step: Optional[str] = None

    pure_add = _extract_binary_addition(lowered)
    if pure_add is not None:
        a, b = pure_add
        entities.operand = float(b)
        steps.append(
            ActionStep(
                step_id=sb.next_id(),
                action=ActionName.ADD_CONSTANT,
                args={"left": float(a), "right": float(b)},
            )
        )
        return ActionPlan(
            user_text=user_text,
            scope=ScopeInfo(),
            intent=IntentInfo(name=IntentName.CALCULATOR_OPERATION, confidence=0.88),
            entities=entities,
            steps=steps,
        )

    slot = _extract_calculator_slot(lowered)
    if slot is not None:
        entities.calculator_slot = slot
        step_id = sb.next_id()
        steps.append(
            ActionStep(
                step_id=step_id,
                action=ActionName.READ_CALCULATOR_RESULT,
                args={"slot": slot},
            )
        )
        prev_step = step_id

    op = _extract_operation(lowered)
    if op is not None:
        action, operand = op
        entities.operand = float(operand)
        step_id = sb.next_id()
        op_args: dict[str, object] = {"operand": float(operand)}
        if prev_step:
            op_args["value_from"] = prev_step
        steps.append(ActionStep(step_id=step_id, action=action, args=op_args))
        prev_step = step_id

    convert = _extract_convert(lowered)
    if convert is not None:
        from_unit, to_unit, literal_value = convert
        entities.source_unit = from_unit
        entities.target_unit = to_unit
        step_id = sb.next_id()
        convert_args: dict[str, object] = {"from_unit": from_unit, "to_unit": to_unit}
        if prev_step:
            convert_args["value_from"] = prev_step
        elif literal_value is not None:
            convert_args["value"] = literal_value
        steps.append(
            ActionStep(
                step_id=step_id, action=ActionName.CONVERT_UNIT, args=convert_args
            )
        )
        prev_step = step_id

    if _wants_journal_write(lowered):
        step_id = sb.next_id()
        journal_args: dict[str, object] = {"content_mode": "auto_from_previous_steps"}
        if prev_step:
            journal_args["value_from"] = prev_step
        steps.append(
            ActionStep(
                step_id=step_id,
                action=ActionName.WRITE_JOURNAL_ENTRY,
                args=journal_args,
            )
        )

    if not steps:
        return None

    intent_name = _infer_action_intent(steps)
    confidence = 0.94 if intent_name == IntentName.TRANSFORM_AND_RECORD_VALUE else 0.88

    return ActionPlan(
        user_text=user_text,
        scope=ScopeInfo(),
        intent=IntentInfo(name=intent_name, confidence=confidence),
        entities=entities,
        steps=steps,
    )


def _build_note_capture(user_text: str) -> Optional[NoteCapture]:
    lowered = user_text.lower()
    if any(hint in lowered for hint in _OBSERVATION_HINTS):
        return NoteCapture(
            user_text=user_text,
            scope=ScopeInfo(),
            intent=IntentInfo(name=IntentName.RECORD_OBSERVATION, confidence=0.96),
            note=NotePayload(note_type=NoteType.OBSERVATION, content=user_text),
            entities=EntityBundle(free_text_value=user_text),
        )

    m = re.search(
        r"(write down|record|log)\s+result\s+([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z]+)?",
        lowered,
    )
    if m:
        val = m.group(2)
        unit = _normalize_unit(m.group(3))
        content = f"result {val}" if unit is None else f"result {val} {unit}"
        return NoteCapture(
            user_text=user_text,
            scope=ScopeInfo(),
            intent=IntentInfo(name=IntentName.RECORD_VALUE, confidence=0.9),
            note=NotePayload(note_type=NoteType.VALUE, content=content),
            entities=EntityBundle(
                free_text_value=content,
                target_unit=unit,
            ),
        )

    if any(w in lowered for w in _WRITE_HINTS):
        return NoteCapture(
            user_text=user_text,
            scope=ScopeInfo(),
            intent=IntentInfo(name=IntentName.RECORD_VALUE, confidence=0.82),
            note=NotePayload(note_type=NoteType.GENERAL, content=user_text),
            entities=EntityBundle(free_text_value=user_text),
        )

    return None


def _build_protocol_plan(user_text: str, protocol_name: str) -> ActionPlan:
    entities = EntityBundle(protocol_name=protocol_name)
    steps = [
        ActionStep(
            step_id="s1",
            action=ActionName.SEARCH_PROTOCOL,
            args={"protocol_name": protocol_name},
        )
    ]
    return ActionPlan(
        user_text=user_text,
        scope=ScopeInfo(),
        intent=IntentInfo(name=IntentName.RETRIEVE_PROTOCOL, confidence=0.93),
        entities=entities,
        steps=steps,
    )


def _build_previous_value_clarification(user_text: str) -> ClarificationNeeded:
    return ClarificationNeeded(
        status=ParseStatus.NEEDS_CLARIFICATION,
        user_text=user_text,
        scope=ScopeInfo(),
        intent=IntentInfo(name=IntentName.RECORD_VALUE, confidence=0.71),
        missing=[
            MissingField(
                field="source_value",
                reason="previous value is ambiguous",
            )
        ],
        ambiguities=[
            Ambiguity(
                field="source_value",
                candidates=["calculator_1_latest", "calculator_2_latest"],
                reason="reference 'previous value' has multiple valid sources",
            )
        ],
    )


def _not_a_command(user_text: str, reason: str) -> ClarificationNeeded:
    return ClarificationNeeded(
        status=ParseStatus.NOT_A_COMMAND,
        user_text=user_text,
        scope=ScopeInfo(),
        intent=IntentInfo(name=IntentName.UNSUPPORTED, confidence=0.2),
        notes=[reason],
    )


def _unsupported(user_text: str) -> ClarificationNeeded:
    return ClarificationNeeded(
        status=ParseStatus.UNSUPPORTED,
        user_text=user_text,
        scope=ScopeInfo(),
        intent=IntentInfo(name=IntentName.UNSUPPORTED, confidence=0.45),
        notes=["input not matched by deterministic parser"],
    )


def _extract_protocol_query(text: str) -> Optional[str]:
    lowered = text.lower()
    if "protocol" not in lowered:
        return None
    m = re.search(
        r"(?:look up|find|search(?: for)?)\s+protocol(?: for)?\s+(.+)", lowered
    )
    if not m:
        return None
    return m.group(1).strip(" .")


def _extract_calculator_slot(text: str) -> Optional[int]:
    m = re.search(r"calculator\s*(\d+)", text)
    if m:
        return int(m.group(1))
    m = re.search(r"slot\s*(\d+)", text)
    if m:
        return int(m.group(1))
    return None


def _extract_operation(text: str) -> Optional[tuple[ActionName, float]]:
    patterns: list[tuple[str, ActionName]] = [
        (r"\badd\s+(-?[0-9]+(?:\.[0-9]+)?)\b", ActionName.ADD_CONSTANT),
        (r"\bsubtract\s+(-?[0-9]+(?:\.[0-9]+)?)\b", ActionName.SUBTRACT_CONSTANT),
        (
            r"\bmultiply(?: by)?\s+(-?[0-9]+(?:\.[0-9]+)?)\b",
            ActionName.MULTIPLY_CONSTANT,
        ),
        (r"\bdivide(?: by)?\s+(-?[0-9]+(?:\.[0-9]+)?)\b", ActionName.DIVIDE_CONSTANT),
    ]
    for pattern, action in patterns:
        m = re.search(pattern, text)
        if m:
            return action, float(m.group(1))
    return None


def _extract_binary_addition(text: str) -> Optional[tuple[float, float]]:
    m = re.search(
        r"\badd\s+(-?[0-9]+(?:\.[0-9]+)?)\s+and\s+(-?[0-9]+(?:\.[0-9]+)?)\b", text
    )
    if not m:
        return None
    return float(m.group(1)), float(m.group(2))


def _extract_convert(text: str) -> Optional[tuple[str, str, Optional[float]]]:
    m = re.search(
        r"\bconvert\s+(-?[0-9]+(?:\.[0-9]+)?)?\s*([a-zA-Z]+)?\s+to\s+([a-zA-Z]+)\b",
        text,
    )
    if not m:
        return None
    literal_value = float(m.group(1)) if m.group(1) else None
    from_unit = _normalize_unit(m.group(2))
    to_unit = _normalize_unit(m.group(3))
    if to_unit is None:
        return None
    if from_unit is None and "liter" in text and "milliliter" in text:
        from_unit = "L"
    if from_unit is None and literal_value is not None:
        from_unit = "value_unit_unknown"
    if from_unit is None:
        return None
    return from_unit, to_unit, literal_value


def _normalize_unit(unit: Optional[str]) -> Optional[str]:
    if not unit:
        return None
    return _UNIT_ALIASES.get(unit.strip().lower(), unit.strip())


def _wants_journal_write(text: str) -> bool:
    return any(
        term in text
        for term in ("write to journal", "write it down", "write down", "journal")
    )


def _is_conversational(text: str) -> bool:
    if any(re.search(rf"\b{re.escape(g)}\b", text) for g in _GREETING_WORDS):
        return True
    return any(re.search(rf"\b{re.escape(w)}\b", text) for w in _CONVERSATIONAL_HINTS)


def _determine_intent_family(user_text: str) -> Optional[IntentName]:
    text = user_text.lower()
    if _extract_protocol_query(user_text):
        return IntentName.RETRIEVE_PROTOCOL
    if _is_ambiguous_previous_value(text):
        return IntentName.RECORD_VALUE
    if (
        _extract_binary_addition(text) is not None
        or _extract_calculator_slot(text) is not None
        or _extract_operation(text) is not None
        or _extract_convert(text) is not None
        or _wants_journal_write(text)
    ):
        return IntentName.CALCULATOR_OPERATION
    if any(hint in text for hint in _OBSERVATION_HINTS):
        return IntentName.RECORD_OBSERVATION
    if any(w in text for w in _WRITE_HINTS):
        return IntentName.RECORD_VALUE
    return None


def _is_ambiguous_previous_value(text: str) -> bool:
    return "previous value" in text or "previous result" in text


def _infer_action_intent(steps: list[ActionStep]) -> IntentName:
    actions = {s.action for s in steps}
    if ActionName.SEARCH_PROTOCOL in actions:
        return IntentName.RETRIEVE_PROTOCOL
    if (
        ActionName.READ_CALCULATOR_RESULT in actions
        and ActionName.CONVERT_UNIT in actions
        and ActionName.WRITE_JOURNAL_ENTRY in actions
    ):
        return IntentName.TRANSFORM_AND_RECORD_VALUE
    if any(
        a in actions
        for a in {
            ActionName.ADD_CONSTANT,
            ActionName.SUBTRACT_CONSTANT,
            ActionName.MULTIPLY_CONSTANT,
            ActionName.DIVIDE_CONSTANT,
        }
    ):
        return IntentName.CALCULATOR_OPERATION
    if ActionName.WRITE_JOURNAL_ENTRY in actions:
        return IntentName.RECORD_VALUE
    return IntentName.CALCULATOR_OPERATION
