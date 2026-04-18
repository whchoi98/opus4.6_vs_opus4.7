#!/bin/bash
# Verify secret-scan.sh blocks known patterns and ignores safe patterns.
#
# Test patterns are CONSTRUCTED AT RUNTIME inside this script rather than
# read from a fixtures file. This prevents real-looking secret patterns
# from being stored in the repository where GitHub's secret scanner might
# flag them on push. The patterns below are obvious test vectors —
# all-A's, all-zeros, or documented EXAMPLE values.

HOOK=".claude/hooks/secret-scan.sh"

check_blocks() {
    local desc="$1"
    local input="$2"
    if echo "$input" | bash "$HOOK" 2>/dev/null; then
        fail "blocks: $desc" "hook allowed the pattern"
    else
        pass "blocks: $desc"
    fi
}

check_allows() {
    local desc="$1"
    local input="$2"
    if echo "$input" | bash "$HOOK" 2>/dev/null; then
        pass "allows: $desc"
    else
        fail "allows: $desc" "hook blocked a safe input"
    fi
}

# --- Synthetic patterns constructed at runtime (not stored in git) ---
# Anthropic API key shape: sk-ant-api03- + ≥80 chars
SYNTHETIC_ANTHROPIC="sk-ant-api03-$(printf 'A%.0s' {1..80})-$(printf '0%.0s' {1..10})"
# Bedrock bearer shape: ABSKQmVkcm9j + ≥80 base64-ish chars
SYNTHETIC_BEDROCK="ABSKQmVkcm9j$(printf 'A%.0s' {1..90})=="
# AWS documentation example keys
SYNTHETIC_AKIA="AKIA-SANITIZED-SYNTHETIC"
SYNTHETIC_ASIA="ASIA-SANITIZED-SYNTHETIC"

# --- True positives — hook should block ---
check_blocks "synthetic anthropic key" "python3 script.py --key=$SYNTHETIC_ANTHROPIC"
check_blocks "synthetic bedrock key" "curl --header 'Authorization: Bearer $SYNTHETIC_BEDROCK'"
check_blocks "AWS example AKIA key" "aws configure set aws_access_key_id $SYNTHETIC_AKIA"
check_blocks "AWS example ASIA key" "aws configure set aws_access_key_id $SYNTHETIC_ASIA"

# --- False positives — hook should allow ---
check_allows "plain run command" "python3 run.py --test all --runs 5"
check_allows "source env file" "source .env.local"
check_allows "git diff" "git diff HEAD~1"
check_allows "pip install" "pip install --user -r requirements.txt"
check_allows "curl public API" "curl https://api.example.com/v1/data"
