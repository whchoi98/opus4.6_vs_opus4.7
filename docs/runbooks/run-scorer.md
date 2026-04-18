# Runbook: Run LLM-judge quality scorer

**Purpose:** Compare 4.7 vs 4.6 response quality on a given prompt using Sonnet 4.6 as judge. Reveals quality differences that token/latency metrics miss.

**When to run:** After a benchmark run to sanity-check whether cost/latency gains came with quality losses. Useful for evaluating tool-use prompts, truncation sensitivity, verbosity differences.

**Estimated time:** ~30 seconds per run × N runs

**Estimated cost:** ~$0.01 per run (Sonnet 4.6 is 0.6x Opus pricing)

**Prerequisites:**
- Valid Bedrock credentials
- Access to `global.anthropic.claude-sonnet-4-6` inference profile in us-east-1

## Procedure

### Step 1: Load credentials

```bash
source .env.local && export $(cut -d= -f1 .env.local)
```

### Step 2: Score a specific prompt type

```bash
python3 score.py --prompt-label tools --runs 5
```

**Prompt labels available:** `tools`, `short`, `proof` (defined in `score.py::PROMPTS`).

**Expected output:** per-run verdict + total cost + output path.

### Step 3: Read report

```bash
cat results/scorer-*/scorer-report.md | head -40
```

**Look for:**
- Position-A win rate in diagnostic section — far from 50% indicates judge bias
- Verdict counts per prompt
- Rationale column for specific reasoning patterns

## Verification

- [ ] `scorer-report.json` contains `position_of_47` field in each result (randomization active)
- [ ] Position A win rate within 40-60% if judge is unbiased; outside that range, flag for review

## Interpreting results

**If 4.6 wins majority but Position A win rate is >60%:**
Consider whether truncation bias (max_tokens cap) favors terser 4.6.

**If verdicts flip on re-run with larger N:**
Sample size too small. Run more iterations.

**If tool-use prompt shows 4.6 dominance:**
4.6 emits tool_use blocks; 4.7 may ask for clarification. Both are valid behaviors — judge rationale will show which style the judge prefers.

## Rollback

N/A.

## References

- Scorer module: `scorers/judge.py`
- V2 findings (A/B randomization): `docs/superpowers/findings/2026-04-18-blog-cross-reference.md`
