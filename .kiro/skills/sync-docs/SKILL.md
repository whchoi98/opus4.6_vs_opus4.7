---
name: sync-docs
description: Synchronize project documentation with current code state. Use when mentioning doc sync, documentation update, or KIRO.md update.
---

# Sync docs

Walk the project and ensure docs reflect the current code state.

## Checklist

1. **KIRO.md / CLAUDE.md project structure:** compare "Project Structure" section to actual directory tree. Add/remove entries.
2. **Test counts:** verify `python3 -m pytest tests/ --collect-only -q | tail -1` matches "N passing" claims in docs.
3. **Case count:** verify case module count matches "N benchmark tests" claim.
4. **`run.py --dry-run --test all`:** copy the "Plan: X cases x N runs = M calls" number into any doc that references total call count.
5. **Findings docs index:** ensure top-level docs link to `docs/test-results.md` latest files.
6. **Known state section:** update cumulative cost, latest commit count.

## Quality scoring (optional)

- Per-module CLAUDE.md present? (clients, cases, runner, scorers, tests)
- Top-level KIRO.md and CLAUDE.md under 200 lines?
- No "TODO" / "TBD" placeholders in committed docs

## When NOT to sync

- Mid-benchmark run (data not yet stable)
- During active test-writing (docs catch up after tests pass)
