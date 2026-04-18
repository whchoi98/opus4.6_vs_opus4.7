# Onboarding

Get the benchmark running locally in ~10 minutes.

## Prerequisites

- **Python 3.9+** (`python3 --version`)
- **AWS credentials** — either `AWS_PROFILE` / IAM role OR a Bedrock API key (`AWS_BEARER_TOKEN_BEDROCK`)
- **Bedrock access** to `global.anthropic.claude-opus-4-6-v1` and `global.anthropic.claude-opus-4-7` in `us-east-1`
- Optional: Anthropic API key with credits (for 1P tests)

## Setup

```bash
# Clone & install
git clone <repo-url>
cd Opus4.6vsOpus4.7
pip install --user -r requirements.txt

# Credentials
cp .env.local.example .env.local
# Edit .env.local — fill in AWS_BEARER_TOKEN_BEDROCK or leave blank and use AWS_PROFILE
chmod 600 .env.local

# Verify install
python3 -c "import anthropic, boto3, rich, dotenv, pytest; print('OK')"

# Run unit tests
python3 -m pytest tests/
# Expected: 62 passed
```

## First run

```bash
# See the plan (no API calls)
python3 run.py --dry-run --test 1 --runs 1
# Expected: Plan: 5 cases × 1 runs = 5 calls

# Actually run one small test (costs ~$0.03)
source .env.local && export $(cut -d= -f1 .env.local)
python3 run.py --test 1 --runs 1
# Expected: report written to results/YYYY-MM-DD-HHMM/
```

## Understanding the structure

See [architecture.md](./architecture.md) for the full component map.

Key files to read in order:
1. `CLAUDE.md` — project-wide conventions
2. `config.py` — model IDs, pricing (39 lines)
3. `cases/base.py` — TestCase dataclass (20 lines)
4. `clients/base.py` — CallResult + response parser (80 lines)
5. `run.py::main` — benchmark execution flow (~200 lines)

## Finding results

```
results/YYYY-MM-DD-HHMM/
├── raw.json          # every individual call
├── aggregated.json   # per-case mean/stdev
├── report.md         # human-readable summary
└── calls/            # per-call request body dumps
```

## Common tasks

- **Add a new benchmark test:** create `cases/<name>.py` with a `cases() -> list[TestCase]` function; register in `runner/dispatch.py`; update `tests/test_runner.py::test_collect_cases_all` count.
- **Modify a prompt:** only `cases/prompts.py`. Never inline.
- **Change retry behavior:** only `runner/execute.py::execute_case_with_retry`.

## Getting help

- See [docs/runbooks/](./runbooks/) for step-by-step procedures
- See [docs/test-results.md](./test-results.md) for result interpretation
- See [docs/decisions/](./decisions/) for architectural decisions
