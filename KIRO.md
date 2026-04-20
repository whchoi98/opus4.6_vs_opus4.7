# Opus 4.7 vs 4.6 Bedrock Benchmark

## Overview

Python benchmark harness that measures Claude Opus 4.7 vs 4.6 behavior on AWS
Bedrock across 13 dimensions: token overhead, latency, TTFT, tool use patterns,
prompt length scaling, multi-turn conversation cost, language/code tokenization,
endpoint parity (Bedrock runtime vs Mantle), auth methods, and response quality
(via LLM-judge). Runs with 5-run averaging and produces JSON + Markdown reports.

## Project Structure

```
.
├── run.py                 # CLI entry (main benchmark loop)
├── score.py               # CLI entry (LLM-judge quality scorer)
├── config.py              # Model IDs, pricing, endpoints
├── stats.py               # CallResult aggregation (mean, stdev)
├── reporter.py            # JSON + Markdown writers
├── clients/               # Backend client wrappers (pure invocation only)
│   ├── base.py            #   CallResult, compute_cost_usd, parse_bedrock_response
│   ├── bedrock_runtime.py #   anthropic.AnthropicBedrock with explicit auth isolation
│   ├── bedrock_mantle.py  #   Raw requests + SigV4('bedrock-mantle')
│   └── anthropic_1p.py    #   anthropic.Anthropic (disabled by default)
├── cases/                 # Benchmark case definitions (pure data)
│   ├── base.py            #   TestCase dataclass
│   ├── prompts.py         #   All prompts + tool schemas (single source of truth)
│   └── *.py               #   Tests 1-13 (effort, length, tools, mantle, etc.)
├── runner/                # Orchestration (retry, dispatch, preflight)
│   ├── preflight.py       #   Auth env validation
│   ├── dispatch.py        #   Case collection from test ID selection
│   └── execute.py         #   Retry loop + client selection cache
├── scorers/               # Quality evaluation (LLM-judge)
│   └── judge.py           #   Pairwise 4.7 vs 4.6 with A/B randomization
├── tests/                 # pytest unit tests (62 tests)
├── docs/                  # Architecture, results, onboarding, ADRs, runbooks
└── results/               # Per-run outputs (gitignored)
```

## Key Commands

```bash
# Run benchmark
python3 run.py --dry-run                      # Plan without API calls
python3 run.py --test all --runs 5            # Full suite
python3 run.py --test 6,7,8 --runs 3          # Specific subset
python3 run.py --report-only results/<dir>    # Regenerate report

# Quality scorer
python3 score.py --prompt-label tools --runs 5

# Tests
python3 -m pytest tests/ -v

# Setup
pip install --user -r requirements.txt
cp .env.local.example .env.local
```

## Conventions

- `from __future__ import annotations` in every module (Python 3.9 compat)
- `@dataclass(frozen=True)` for data-only types (CallResult, TestCase, CaseAggregate)
- TDD: every module has a pytest test file before implementation
- No retry in client modules; retries live only in `runner/execute.py`
- All prompts and tool schemas in `cases/prompts.py` (never inline)
- `.env.local` is gitignored (permissions 600); never commit real keys
- Commit messages: `feat(<scope>):`, `fix(<scope>):`, `docs(<scope>):`

## Sync Rules

- New test added -> register in `runner/dispatch.py`, update test count in `tests/test_runner.py`
- New finding -> update `docs/test-results.md` consolidated report
- New module added -> create CLAUDE.md in that directory
- Architecture decision -> create `docs/decisions/ADR-NNN-title.md`
