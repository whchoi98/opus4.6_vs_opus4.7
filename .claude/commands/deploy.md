---
name: deploy
description: Run a full benchmark "deployment" — execute the benchmark and produce a release snapshot
---

For this project, "deploy" means running the full benchmark as a reproducible
snapshot, not deploying infrastructure.

1. Check `git status` — must be clean before deploying.
2. Run `python3 -m pytest tests/` — must pass before calling out to Bedrock.
3. Load `.env.local` credentials.
4. Run `python3 run.py --test all --runs 5` — ~15-20 min, ~$4.
5. On completion, read `results/<latest>/report.md`.
6. Suggest findings doc location: `docs/test-results.md`.
7. Use the `release` skill to tag and commit the snapshot.

If any step fails, stop and report the failure. Do NOT auto-retry — the user
decides whether to rerun (costs real money on each call).
