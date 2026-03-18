# Legacy Archive

This directory stores previously active project components that were archived as part of the modular runtime migration.

## Archived Directories

- `agents/`
  - Previous unified FastAPI backend entrypoint (`agents/controller.py`).
  - Included legacy SQLite session/utterance/action orchestration.
- `ai-lab-journal - open source/`
  - Legacy external scaffold/assets kept for reference.
- `papers/`
  - Research/reference papers not required for active runtime modules.

## Why Archived

The active development model is now modular and stage-based:

- `context_action_plan/`
- `plan_validation/`
- `executor_runtime/`
- `mock_runtime_contract/`
- `db/`
- `tools/`
- `stt/`

The old unified backend path was retired to avoid mixing legacy and staged runtime flows.

## Restore Instructions

If needed, restore components with `git mv`, for example:

```bash
git mv archive/legacy/agents agents
```

Likewise for other archived directories:

```bash
git mv "archive/legacy/ai-lab-journal - open source" "ai-lab-journal - open source"
git mv archive/legacy/papers papers
```

