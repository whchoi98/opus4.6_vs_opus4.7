# Runbook: Run full benchmark

**Purpose:** Execute the 13-test Opus 4.7 vs 4.6 benchmark suite end-to-end and produce a report.

**When to run:** On major changes to case modules / clients. When reproducing blog claims. Before sharing findings externally.

**Estimated time:** 15–25 minutes

**Estimated cost:** $4–6 (for `--test all --runs 5`)

**Prerequisites:**
- `.env.local` with `AWS_BEARER_TOKEN_BEDROCK` or `AWS_PROFILE` / IAM role
- `AWS_REGION=us-east-1`
- `python3 -m pytest tests/` passes (62 tests)

## Procedure

### Step 1: Load credentials

```bash
cd /home/ec2-user/my-project/Opus4.6vsOpus4.7
source .env.local && export $(cut -d= -f1 .env.local)
```

**If it fails:** file missing → `cp .env.local.example .env.local` and fill in.

### Step 2: Dry-run

```bash
python3 run.py --dry-run --test all --runs 5
```

**Expected:** `Plan: 69 cases × 5 runs = 345 calls` (Test 5 excluded by default). Cost estimate printed.

### Step 3: Execute

```bash
python3 run.py --test all --runs 5 2>&1 | tee /tmp/benchmark.log
```

**Expected output:** progress bar reaches 100%, final line `Done. Wrote results/YYYY-MM-DD-HHMM/report.md`.

**If it fails mid-run:** `KeyboardInterrupt` saves partial data. Re-run will create a new results dir; don't re-run already-completed cases manually (cost waste).

### Step 4: Inspect results

```bash
RESULTS=$(ls -td results/*/ | head -1)
cat "$RESULTS/report.md" | head -60
```

### Step 5: Error check

```bash
python3 -c "
import json
from pathlib import Path
d = sorted(Path('results').iterdir())[-1]
raw = json.loads((d/'raw.json').read_text())
errs = [r for r in raw['results'] if r.get('error')]
print(f'{len(errs)}/{len(raw[\"results\"])} errored')
"
```

**If errors > 0:** most common cause is Mantle endpoint returning 404 (account not allowlisted). Document in divergence log.

## Verification

- [ ] `results/<ts>/report.md` exists
- [ ] Test 1 input tokens identical across 4 effort levels (key blog claim)
- [ ] No unexpected error bursts
- [ ] Total cost within 20% of estimate

## Rollback

N/A — benchmark is read-only against Bedrock API.

## References

- Design spec: `docs/superpowers/specs/2026-04-18-opus-47-vs-46-benchmark-design.md`
- Latest findings: `docs/superpowers/findings/`
