#!/bin/bash
# Verify secret-scan.sh blocks known patterns and ignores safe patterns.

HOOK=".claude/hooks/secret-scan.sh"

# True positives — should block (exit non-zero)
check_blocks() {
    local desc="$1"
    local input="$2"
    if echo "$input" | bash "$HOOK" 2>/dev/null; then
        fail "blocks: $desc" "hook allowed the secret"
    else
        pass "blocks: $desc"
    fi
}

# False positives — should allow (exit zero)
check_allows() {
    local desc="$1"
    local input="$2"
    if echo "$input" | bash "$HOOK" 2>/dev/null; then
        pass "allows: $desc"
    else
        fail "allows: $desc" "hook blocked a safe input"
    fi
}

# True positives — samples from tests/fixtures/secret-samples.txt
if [ -f tests/fixtures/secret-samples.txt ]; then
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        check_blocks "secret pattern: ${line:0:20}..." "python3 script.py --key=$line"
    done < tests/fixtures/secret-samples.txt
fi

# False positives
if [ -f tests/fixtures/false-positives.txt ]; then
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        check_allows "safe pattern: ${line:0:40}" "$line"
    done < tests/fixtures/false-positives.txt
fi
