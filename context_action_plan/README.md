# context_action_plan

Deterministic parser for the stage after STT:

`raw transcript text -> semantic context -> normalized ParsedOutput`

## Purpose

Provide a stable, production-oriented contract for downstream execution without calling an LLM yet.

## What It Returns

`parse_transcript(text: str) -> ParsedOutput` where `ParsedOutput` is one of:

- `ActionPlan`
- `NoteCapture`
- `ClarificationNeeded`

All outputs are pydantic models and JSON serializable.

## Input / Output Contract

Input:
- `text: str` (raw transcript from STT or any plain text source)

Output:
- `ParsedOutput` (`ActionPlan | NoteCapture | ClarificationNeeded`)
- Contract status is carried in `status` (`ready`, `needs_clarification`, `recognized_but_unimplemented`, `not_a_command`, `unsupported`)
- No side effects; pure parse result only

## What It Does Not Do Yet

- No database reads/writes
- No UI state dependencies
- No tool execution
- No SQL generation
- No external API calls

## Run Tests

From repo root:

```bash
uv run pytest context_action_plan/tests -q
```
