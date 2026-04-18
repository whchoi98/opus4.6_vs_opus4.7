# Opus 4.7 vs 4.6 Benchmark

Reproduces the Apr 17, 2026 field-report comparison of Claude Opus 4.7 and
Opus 4.6 on AWS Bedrock. Measures token overhead, latency, thinking-block
visibility, parallel tool-use cost, and Mantle endpoint parity.

## Quick start

```bash
cp .env.local.example .env.local
# Fill in AWS_BEARER_TOKEN_BEDROCK or AWS credentials, AWS_REGION=us-east-1
# Optionally: ANTHROPIC_API_KEY (1P tests — not supported by default)

pip install -r requirements.txt

python run.py --dry-run              # see the plan
python run.py --test all --runs 5    # run everything (~15–30 min, ~$1–2)
```

## CLI options

- `--test` — `all` or comma-separated subset (`1,2,3,4`)
- `--runs` — number of runs per case (default 5)
- `--backend` — `bedrock` (default) or `1p` (currently disabled)
- `--dry-run` — print plan only, no API calls
- `--no-save-bodies` — disable per-call body dumps (default on)
- `--report-only <dir>` — regenerate `report.md` from existing `raw.json`

## Project structure

```
.
├── run.py                 # CLI entry point
├── config.py              # Model IDs, pricing, endpoints
├── clients/               # Backend client wrappers
│   ├── base.py            #   CallResult + response parser
│   ├── bedrock_runtime.py #   AnthropicBedrock SDK wrapper
│   ├── bedrock_mantle.py  #   Raw HTTP + SigV4 (service name "bedrock-mantle")
│   └── anthropic_1p.py    #   Anthropic direct API
├── cases/                 # Benchmark case definitions
│   ├── base.py            #   TestCase dataclass
│   ├── prompts.py         #   All prompts + tool schemas
│   ├── effort.py          #   Test 1 cases
│   ├── length.py          #   Test 2 cases
│   ├── tools.py           #   Test 3 cases
│   └── mantle.py          #   Test 4 cases
├── runner/                # Orchestration
│   ├── preflight.py       #   Auth validation
│   ├── dispatch.py        #   Case collection
│   └── execute.py         #   Retry + client selection
├── stats.py               # Aggregation (mean, stdev)
├── reporter.py            # JSON + Markdown output
├── tests/                 # pytest unit tests (43 tests)
└── results/               # Per-run outputs (gitignored)
    └── YYYY-MM-DD-HHMM/
        ├── raw.json
        ├── aggregated.json
        ├── report.md
        └── calls/         # Per-call body dumps
```

## Design spec and plan

- `docs/superpowers/specs/2026-04-18-opus-47-vs-46-benchmark-design.md` — full design
- `docs/superpowers/plans/2026-04-18-opus-47-vs-46-benchmark.md` — implementation plan
- `docs/superpowers/findings/` — observed divergences from the blog

## Known limitations

See `docs/superpowers/findings/2026-04-18-first-run-divergences.md` for divergences
observed between our reproduction and the source blog. Key ones:

1. **Mantle endpoint requires account allowlisting** — returns HTTP 404 by default.
2. **Opus 4.6 thinking blocks not surfaced** — our default invocation omits `thinking`
   kwarg; to reproduce the blog's 856-char thinking output, add `thinking={"type":
   "enabled", "budget_tokens": N}` in `clients/bedrock_runtime.build_kwargs`.
3. **1P (`anthropic.Anthropic`) disabled** — requires Anthropic API credits.
