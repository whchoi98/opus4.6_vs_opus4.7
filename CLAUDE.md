# CLAUDE.md

Project memory for the Opus 4.7 vs 4.6 Bedrock benchmark harness.

## Project overview

Python benchmark harness that measures Claude Opus 4.7 vs 4.6 behavior on AWS
Bedrock across 13 dimensions: token overhead, latency, TTFT, tool use patterns,
prompt length scaling, multi-turn conversation cost, language/code tokenization,
endpoint parity (Bedrock runtime vs Mantle), auth methods, and response quality
(via LLM-judge). Runs with 5-run averaging and produces JSON + Markdown reports.

Primary use: measure Bedrock-specific behavior of Opus 4.7 vs 4.6 for
production decision-making, using consistent 5-run averaging.

## Tech stack

- Python 3.9+
- `anthropic` SDK 0.96+ — Bedrock + Anthropic direct clients
- `boto3` / `botocore` — AWS credentials + SigV4 signing for Mantle endpoint
- `requests` — raw HTTP for Mantle (SDK doesn't support service name `bedrock-mantle`)
- `rich` — CLI progress display
- `python-dotenv` — `.env.local` loader
- `pytest` — 62 unit tests

## Project structure

```
.
├── run.py                 # CLI entry (main benchmark loop)
├── score.py               # CLI entry (LLM-judge quality scorer)
├── config.py              # Model IDs, pricing, endpoints
├── stats.py               # CallResult aggregation (mean, stdev)
├── reporter.py            # JSON + Markdown writers
├── clients/               # Backend client wrappers — pure invocation only
│   ├── base.py            #   CallResult, compute_cost_usd, parse_bedrock_response
│   ├── bedrock_runtime.py #   anthropic.AnthropicBedrock with explicit auth isolation
│   ├── bedrock_mantle.py  #   Raw requests + SigV4('bedrock-mantle'); bearer token path
│   └── anthropic_1p.py    #   anthropic.Anthropic (disabled by default at runtime)
├── cases/                 # Benchmark case definitions — pure data (cases() lists)
│   ├── base.py            #   TestCase dataclass
│   ├── prompts.py         #   All prompts + tool schemas (single source of truth)
│   ├── effort.py          #   Test 1 — effort level (low/med/high/max)
│   ├── length.py          #   Test 2 — short/long prompts
│   ├── tools.py           #   Test 3 — parallel tool use baseline
│   ├── mantle.py          #   Test 4 — runtime vs mantle + auth comparison
│   ├── caching.py         #   Test 5 — user prompt caching (DEFERRED, 0 cache tokens)
│   ├── multiturn.py       #   Test 6 — 1/3/5/10-turn conversations
│   ├── streaming.py       #   Test 7 — TTFT via messages.stream()
│   ├── tools_scaling.py   #   Test 8 — 1/5/20 tool schemas
│   ├── tool_forcing.py    #   Test 9 — passive/imperative/tool_choice variants
│   ├── multiturn_extreme.py  # Test 10 — 10/20/30/50/100 turns
│   ├── language_code.py   #   Test 11 — English/Korean/code/hybrid
│   ├── system_caching.py  #   Test 12 — system prompt caching (DEFERRED)
│   └── multiturn_knee.py  #   Test 13 — 11/13/15/17/19 turn knee-point
├── runner/                # Orchestration — retry, dispatch, preflight
│   ├── preflight.py       #   Auth env validation (IAM or Bedrock API key)
│   ├── dispatch.py        #   Case collection from test ID selection
│   └── execute.py         #   Retry loop + client selection cache
├── scorers/               # Quality evaluation — LLM-judge
│   └── judge.py           #   Pairwise 4.7 vs 4.6 with A/B randomization
├── tests/                 # pytest unit tests (62 tests)
├── docs/
│   ├── architecture.md    # System architecture (bilingual)
│   ├── test-results.md    # Consolidated benchmark results (bilingual)
│   ├── onboarding.md      # Developer onboarding
│   ├── decisions/         # Architecture Decision Records (ADRs)
│   └── runbooks/          # Operational runbooks
└── results/               # Per-run outputs (gitignored)
    └── YYYY-MM-DD-HHMM/
        ├── raw.json
        ├── aggregated.json
        ├── report.md
        └── calls/
```

## Key commands

```bash
# Run benchmark
python3 run.py --dry-run                      # Plan without API calls
python3 run.py --test all --runs 5            # Full suite (Tests 1-4, 6-13; Test 5 deferred)
python3 run.py --test 6,7,8 --runs 3          # Specific subset
python3 run.py --test 5 --runs 5              # Run deferred test explicitly
python3 run.py --report-only results/2026-04-18-0747  # Regenerate report

# Quality scorer
python3 score.py --prompt-label tools --runs 5

# Tests
python3 -m pytest tests/ -v

# Setup
pip install --user -r requirements.txt
cp .env.local.example .env.local   # Then fill in AWS credentials + API keys
```

## Conventions

- **Type annotations:** `from __future__ import annotations` in every module (Python 3.9 compat).
- **Dataclasses:** `@dataclass(frozen=True)` for data-only types (CallResult, TestCase, CaseAggregate).
- **TDD:** Every module has a pytest unit test file before implementation.
- **No retry in client modules:** Retries live only in `runner/execute.py`.
- **Prompts in single source:** All prompts and tool schemas in `cases/prompts.py`. Never inline.
- **Secrets:** `.env.local` is gitignored (permissions 600). Never commit real keys.
- **Commit messages:** Prefix with `feat(<scope>):`, `fix(<scope>):`, `docs(<scope>):`. Multi-line allowed for detailed change rationale.

## Auto-Sync Rules

When Plan Mode exits with approved plan, ensure related docs exist or are updated:
- New test → add to `cases/`, register in `runner/dispatch.py`, update test count in `tests/test_runner.py`
- Finding → update `docs/test-results.md` consolidated report

## Known state

- **62 pytest tests passing**
- **13 benchmark tests** (Test 5 deferred — Bedrock caching returns 0 tokens)
- **3 real benchmark runs** in `results/` directories
- **Consolidated results** in `docs/test-results.md` (bilingual, 608 lines)
- Cumulative benchmark cost across all runs: ~$7.14
