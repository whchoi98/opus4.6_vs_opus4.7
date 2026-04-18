---
name: release
description: Tag a benchmark "release" — a reproducible snapshot of config + results. Use when finalizing a benchmark run for sharing or publishing.
---

# Release

For this project, "release" = tagging a reproducible benchmark snapshot,
not software versioning.

## When to release

- After a full `--test all --runs 5` run completes successfully
- When a set of findings is ready to share externally (blog, customer call)
- Before making breaking changes to case modules or client wrappers

## Steps

1. Verify clean state: `git status` (no uncommitted changes)
2. Run full suite: `python3 run.py --test all --runs 5`
3. Note results dir: `results/YYYY-MM-DD-HHMM/`
4. Create findings doc if novel results: `docs/superpowers/findings/YYYY-MM-DD-<topic>.md`
5. Commit: `docs: release <label> with <N> findings`
6. Tag: `git tag -a benchmark-YYYY-MM-DD -m "Snapshot: <brief>"`
7. Update CLAUDE.md "Known state" section with latest cumulative cost and test count

## Artifacts to include

- Commit hash of `run.py` + `config.py` + `cases/*` at time of run
- SDK version (`anthropic.__version__`) — already in meta of raw.json
- AWS region (from raw.json meta)
- Total cost, duration, success rate
- Link to findings doc that interprets the numbers
