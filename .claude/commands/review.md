---
name: review
description: Code review the current git diff
---

Review the current git diff against project conventions.

1. Run `git diff` to see unstaged changes. If empty, run `git diff HEAD~1..HEAD`.
2. Use the `code-review` skill to evaluate.
3. Report: strengths, issues by severity, specific file:line fixes, final verdict.
4. If tests are missing for new code, flag as Critical.
