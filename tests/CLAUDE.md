# tests/

Pytest unit tests for the harness itself (not the benchmark cases).

## Rules

- **One test file per source module:** `clients/base.py` ↔ `tests/test_clients_base.py`.
- **No API calls in unit tests.** Test `build_kwargs` functions, dataclass behavior, stats aggregation, CLI arg parsing. Real API exercise happens in `run.py` with smoke test.
- **Use `monkeypatch` for env vars** — don't set real env in tests.

## Files

- `test_config.py` — MODELS_1P/3P, PRICING, `model_key_from_id`.
- `test_clients_base.py` — CallResult dataclass, compute_cost_usd, parse_bedrock_response.
- `test_bedrock_runtime.py` — build_kwargs branching (4.7 adaptive vs 4.6 plain).
- `test_bedrock_mantle.py` — build_body branching.
- `test_anthropic_1p.py` — build_kwargs_1p branching.
- `test_stats.py` — aggregate_results (means, stdevs, error exclusion, grouping key).
- `test_cases.py` — all case modules return correctly-shaped TestCase lists.
- `test_runner.py` — collect_cases counts, check_auth_env branches, resolve_tests set.
- `test_runner_execute.py` — select_client caching, retry behavior with mocked SDK.
- `test_reporter.py` — JSON writers + Markdown shape.
- `test_scorer.py` — verdict parsing.

## Running

```bash
python3 -m pytest tests/ -v
# Current baseline: 62 passed
```

## Adding tests

When you add a module in `clients/`, `cases/`, `runner/`, or `scorers/`,
create a matching `tests/test_<module>.py` **before** writing the module
(TDD — red → green → refactor).
