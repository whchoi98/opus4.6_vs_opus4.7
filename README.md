# Opus 4.7 vs 4.6 Benchmark Harness

Python harness that measures **Claude Opus 4.7 vs Opus 4.6** behavior on
**AWS Bedrock** across 13 test dimensions, with 5-run averaging and
structured JSON + Markdown reports.

Originally built to reproduce the public "4.7 tokenizer costs" blog claims
and extend them with auth-method, multi-turn, tool-forcing, knee-point,
language-decomposition, and quality-judge measurements.

## Quick start

```bash
cp .env.local.example .env.local
# Fill in AWS_BEARER_TOKEN_BEDROCK (or use AWS_PROFILE / IAM role)
# Optional: ANTHROPIC_API_KEY (1P — currently disabled at runtime)

pip install --user -r requirements.txt

python3 run.py --dry-run                 # See the plan
python3 run.py --test all --runs 5       # Full suite (~15-25 min, ~$5)
python3 score.py --prompt-label tools    # LLM-judge quality check
```

## What's measured

| # | Test | Finding |
|---|---|---|
| 1 | Effort level vs input tokens | ✅ effort does NOT affect input |
| 2 | Short vs long prompt | Overhead varies by content (+13% to +57%) |
| 3 | Parallel tool use (baseline) | 4.7 refused tools; 4.6 used 4 |
| 4 | Bedrock Runtime vs Mantle + auth | Mantle unreachable in test account |
| 5 | User prompt caching | **DEFERRED** (cache tokens = 0 on Bedrock) |
| 6 | Multi-turn 1-10 turns | 4.7 latency plateau at 4s up to 10 turns |
| 7 | Streaming TTFT | 4.7 = 1.15s, invariant to prompt length |
| 8 | Tool schema scaling (1/5/20) | 4.7 abandons tools at 20 tools |
| 9 | Tool forcing (prompt vs tool_choice) | `tool_choice="any"` fixes 4.7 |
| 10 | Multi-turn 10-100 turns | Step function at turn 20 |
| 11 | English/Korean/code tokenization | Korean +5%, Python +29%, English +57% |
| 12 | System prompt caching | **DEFERRED** (same as Test 5) |
| 13 | Multi-turn knee-point (11-19) | Confirms step function at 20 |

Plus a **quality scorer** (`score.py`) that pairs 4.7 vs 4.6 responses and
asks Sonnet 4.6 to judge — with A/B randomization to mitigate position bias.

## CLI options

### `run.py`

- `--test` — `all` or comma-separated subset (`1,3,6`)
- `--runs` — number of runs per case (default 5)
- `--backend` — `bedrock` (default) or `1p` (currently blocked — no API credits)
- `--dry-run` — print plan only
- `--no-save-bodies` — disable per-call body dumps (default on)
- `--report-only <dir>` — regenerate `report.md` from existing `raw.json`

### `score.py`

- `--prompt-label` — `tools`, `short`, `proof`
- `--runs` — number of pairwise judgements
- `--output` — output dir

## Results layout

```
results/YYYY-MM-DD-HHMM/
├── raw.json          # Every individual call
├── aggregated.json   # Per-case mean/stdev
├── report.md         # Human-readable summary
└── calls/            # Per-call request body dumps
```

## Documentation

- **Architecture:** [docs/architecture.md](./docs/architecture.md)
- **Onboarding:** [docs/onboarding.md](./docs/onboarding.md)
- **Design spec:** [docs/superpowers/specs/](./docs/superpowers/specs/)
- **Implementation plan:** [docs/superpowers/plans/](./docs/superpowers/plans/)
- **Findings:** [docs/superpowers/findings/](./docs/superpowers/findings/) — 5 docs with results interpretation
- **Runbooks:** [docs/runbooks/](./docs/runbooks/)
- **Decisions:** [docs/decisions/](./docs/decisions/)

## Tech stack

Python 3.9+, `anthropic` SDK 0.96+, `boto3`/`botocore`, `requests`, `rich`,
`python-dotenv`, `pytest` (62 tests).

## License

Internal project, no license declared.
