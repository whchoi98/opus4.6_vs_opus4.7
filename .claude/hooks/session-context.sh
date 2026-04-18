#!/bin/bash
# SessionStart hook — loads project context for Claude.
# Runs once per session at startup. Exit silently on error (non-blocking).

set +e

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$PROJECT_ROOT" || exit 0

echo "## Project: Opus 4.7 vs 4.6 Bedrock benchmark"
echo ""

# Git state
BRANCH=$(git branch --show-current 2>/dev/null)
COMMITS=$(git rev-list --count HEAD 2>/dev/null)
if [ -n "$BRANCH" ]; then
  echo "- Branch: $BRANCH, commits: $COMMITS"
fi

# Test count
if [ -f pyproject.toml ]; then
  TESTS=$(find tests -name 'test_*.py' 2>/dev/null | wc -l)
  echo "- Pytest files: $TESTS"
fi

# Benchmark test count (cases/)
if [ -d cases ]; then
  CASES=$(find cases -name '*.py' -not -name '__init__.py' -not -name 'base.py' -not -name 'prompts.py' 2>/dev/null | wc -l)
  echo "- Benchmark test modules: $CASES"
fi

# Latest results dir
LATEST=$(ls -td results/*/ 2>/dev/null | head -1)
if [ -n "$LATEST" ]; then
  echo "- Latest benchmark run: $LATEST"
fi

# Findings docs
FINDINGS=$(find docs/superpowers/findings -name '*.md' 2>/dev/null | wc -l)
if [ "$FINDINGS" -gt 0 ]; then
  echo "- Findings docs: $FINDINGS"
fi

echo ""
echo "Key entry points: run.py (benchmark), score.py (quality scorer)"
echo "Latest findings: docs/superpowers/findings/"

exit 0
