---
name: test-all
description: Run the full pytest suite + benchmark dry-run
---

Execute the full project test suite.

1. **Unit tests:** `python3 -m pytest tests/ -v` — must show all passing.
2. **Benchmark dry-run:** `python3 run.py --dry-run --test all --runs 5` — verifies case registration and resolves planned call count.
3. **Scorer import check:** `python3 -c "from scorers.judge import score_pairwise; print('OK')"` — verifies scorer module is importable.

Report: N tests passed, total cases × runs from dry-run, any failures.
If all pass, suggest next action; if failure, show specific pytest output with file:line.
