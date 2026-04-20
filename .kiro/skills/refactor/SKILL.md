---
name: refactor
description: Refactor code while preserving behavior. Use when mentioning refactoring, code cleanup, or code improvement.
---

# Refactor

Improve code structure without changing observable behavior.

## Principles for this project

- **Single-responsibility modules**: `clients/*.py` invoke only, `cases/*.py` data only, `runner/*.py` orchestration only. Don't blur.
- **Frozen dataclasses** for values; don't add mutation to CallResult / TestCase / CaseAggregate.
- **No retry logic in clients**: if you see retry in a client wrapper, move it to `runner/execute.py`.
- **Tests first**: before refactoring, verify existing tests pass. After refactoring, rerun and compare.

## Workflow

1. `pytest tests/` — establish green baseline
2. Make minimal change
3. `pytest tests/` — verify still green
4. Commit with `refactor(<scope>): <description>`

## Red flags to fix

- Duplicated prompt strings → move to `cases/prompts.py`
- Inline magic numbers → add to `config.py`
- `client._client.messages.create(...)` called outside the wrapper class → extract to a method
- File grew past ~200 lines without clear sub-responsibility → consider splitting
