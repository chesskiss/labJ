# plan_validation

Validates parsed outputs from `context_action_plan` against an approved tool registry contract.

## Purpose

Checks whether a parsed output is structurally executable and contract-compliant.

## Parser vs Validator

- Parser (`context_action_plan`): decides semantic structure from transcript text.
- Validator (`plan_validation`): checks that structure against strict execution rules.

## Tool Registry

The registry defines allowed actions, argument contracts, and lightweight metadata.
Validation fails when plans reference unknown actions or violate tool arg rules.

## Input / Output Contract

Input:
- `parsed: ParsedOutput` (from `context_action_plan`)
- optional `registry: ToolRegistry` (defaults to built-in registry)

Output:
- `ValidationResult`
- Key fields:
  - `is_valid`: structural correctness
  - `is_executable`: safe to send to executor
  - `errors` / `warnings`: structured issues with stable codes
- No execution; no runtime mutation

## What This Module Does Not Do

- No DB access
- No tool execution
- No UI logic
- No network calls

## Run tests

```bash
uv run pytest plan_validation/tests -q
```
