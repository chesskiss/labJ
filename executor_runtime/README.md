# Executor Runtime

Purpose: execute **validated** plans against an in-memory mocked tool/runtime layer.

Stage split:
- Parser (`context_action_plan`) decides transcript meaning.
- Validator (`plan_validation`) checks structural executability.
- Executor (`executor_runtime`) runs steps against runtime state and returns runtime success/failure.

What this module returns:
- `ExecutionResult` with status (`succeeded` / `failed` / `not_executed`), `step_results`, and optional structured runtime error.

## Input / Output Contract

Input:
- `parsed: ParsedOutput` (typically an `ActionPlan`)
- `validation: ValidationResult` (from `plan_validation`)
- `runtime: MockRuntime` (in-memory state used by mocked tools)

Primary API:
- `execute_validated_output(parsed, validation, runtime) -> ExecutionResult`

Output:
- `ExecutionResult`
- `status`: `succeeded | failed | not_executed`
- `step_results`: per-step structured outputs by `step_id`
- `error`: structured runtime failure when execution fails

What this module does not do yet:
- no real DB persistence
- no network calls
- no UI integration
- no real repositories

Run tests:

```bash
uv run pytest executor_runtime/tests -q
```
