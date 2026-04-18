# cases/

Benchmark test definitions. **Pure data** — no execution logic, no API calls.

## Rules

- **Every module exports `cases() -> list[TestCase]`.** That's the entire public interface.
- **Prompts come from `prompts.py`.** Never inline a prompt in a case module.
- **Tool schemas come from `prompts.py`.** Same rule.
- **Each `TestCase` has a unique `name`.** Names are used as file stems for `results/<ts>/calls/*.json`.

## Files

- `base.py` — `TestCase` frozen dataclass (13 fields).
- `prompts.py` — all prompts, tool schemas, system prompts.
- `effort.py` (Test 1), `length.py` (Test 2), `tools.py` (Test 3), `mantle.py` (Test 4), `caching.py` (Test 5 deferred), `multiturn.py` (Test 6), `streaming.py` (Test 7), `tools_scaling.py` (Test 8), `tool_forcing.py` (Test 9), `multiturn_extreme.py` (Test 10), `language_code.py` (Test 11), `system_caching.py` (Test 12 deferred), `multiturn_knee.py` (Test 13).

## Deferred tests

- **Test 5 (user prompt caching)** and **Test 12 (system prompt caching)**: Bedrock does not return `cache_creation_input_tokens` / `cache_read_input_tokens` in responses. Infrastructure in place; runs return 0. Excluded from `--test all` default. Runnable with `--test 5` or `--test 12` for investigation.

## Adding a new test

1. Create `cases/<name>.py` with `from cases.base import TestCase` and `def cases() -> list[TestCase]`.
2. Use constants from `cases.prompts` — add new prompts there if needed.
3. Pick the next free `test_id` (e.g., `"test_14"`).
4. Register in `runner/dispatch.py::TEST_MODULES` with the matching numeric key.
5. Update `run.py::resolve_tests` to include the new id.
6. Update `tests/test_runner.py` and `tests/test_cases.py` with count assertions.
