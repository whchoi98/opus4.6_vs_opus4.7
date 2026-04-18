---
name: code-review
description: Review recent code changes against project conventions. Use when the user asks for code review, says "review this", or is about to commit/push.
---

# Code review

Review recent changes (unstaged or specified commit range) against this
project's conventions.

## Scope

- Python 3.9 syntax compat (no `X | Y` union types without `from __future__ import annotations`)
- Frozen dataclasses for data types (`@dataclass(frozen=True)`)
- No retry logic in `clients/` (only in `runner/execute.py`)
- Prompts centralized in `cases/prompts.py` — flag inline prompt strings elsewhere
- Tests: every new module must have a matching `tests/test_<module>.py`

## How to run

1. Identify changes: `git diff` (unstaged) or `git diff <base>..HEAD`
2. For each changed Python file, check:
   - Imports follow: stdlib → third-party → local
   - Type annotations present on public functions
   - No print statements (use `console.print` from rich)
   - No silent exception handling (`except Exception: pass`)
3. Run `pytest tests/` — must pass before approval
4. Check git log format: `feat(scope):`, `fix(scope):`, `docs(scope):`

## Output format

- Strengths (1-3 bullets)
- Issues grouped by severity: Critical / Important / Minor
- Each issue: file:line reference + concrete fix suggestion
- Final: ✅ Approved / ❌ Needs fixes
