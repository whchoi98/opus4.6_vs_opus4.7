#!/bin/bash
# TAP-style integration test runner for hook + structure tests.
# Run from project root: bash tests/run-all.sh

set +e  # continue on test failures
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Assertion helpers (TAP-style)
pass() {
    TESTS_RUN=$((TESTS_RUN + 1))
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo "ok $TESTS_RUN - $1"
}

fail() {
    TESTS_RUN=$((TESTS_RUN + 1))
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo "not ok $TESTS_RUN - $1"
    [ -n "$2" ] && echo "# $2"
}

assert_file_exists() {
    if [ -f "$1" ]; then
        pass "file exists: $1"
    else
        fail "file exists: $1" "missing"
    fi
}

assert_executable() {
    if [ -x "$1" ]; then
        pass "executable: $1"
    else
        fail "executable: $1" "not executable or missing"
    fi
}

assert_pattern_not_found() {
    # args: pattern, file, description
    if grep -q "$1" "$2" 2>/dev/null; then
        fail "$3" "pattern '$1' found in $2"
    else
        pass "$3"
    fi
}

# Export helpers so sub-scripts can use them
export -f pass fail assert_file_exists assert_executable assert_pattern_not_found
export TESTS_RUN TESTS_PASSED TESTS_FAILED

echo "TAP version 13"

# Run all test scripts
for t in tests/hooks/test-*.sh tests/structure/test-*.sh; do
    [ -f "$t" ] && bash "$t"
done

echo ""
echo "# Run: $TESTS_RUN  Passed: $TESTS_PASSED  Failed: $TESTS_FAILED"
[ "$TESTS_FAILED" -eq 0 ] && exit 0 || exit 1
