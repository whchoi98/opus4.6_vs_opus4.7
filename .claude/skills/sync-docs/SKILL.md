---
name: sync-docs
description: Synchronize docs with current code state. Use when the user says /sync-docs or notices stale documentation.
---

# Sync docs

Walk the project and ensure docs reflect the current code state.

## Checklist

1. **CLAUDE.md project structure:** compare "Project structure" section to `ls -d */` output. Add/remove entries.
2. **Test counts:** verify `python3 -m pytest tests/ --collect-only -q | tail -1` matches "N passing" claims in docs.
3. **Case count in CLAUDE.md:** verify `len(cases/*.py) - 2` (exclude base.py, prompts.py) matches "N benchmark tests" claim.
4. **`run.py --dry-run --test all`:** copy the "Plan: X cases × N runs = M calls" number into any doc that references total call count.
5. **Findings docs index:** ensure top-level docs link to `docs/superpowers/findings/` latest files.
6. **Known state section:** update cumulative cost, latest commit count.

## Quality scoring (optional)

- Per-module CLAUDE.md present? (clients, cases, runner, scorers, tests)
- Top-level CLAUDE.md under 200 lines? (if not, summarize)
- No "TODO" / "TBD" placeholders in committed docs

## When NOT to sync

- Mid-benchmark run (data not yet stable)
- During active test-writing (docs catch up after tests pass)
