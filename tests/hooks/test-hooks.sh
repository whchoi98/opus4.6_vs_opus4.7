#!/bin/bash
# Validate hook scripts exist, are executable, and are registered in settings.json

assert_file_exists .claude/hooks/session-context.sh
assert_executable .claude/hooks/session-context.sh
assert_file_exists .claude/hooks/secret-scan.sh
assert_executable .claude/hooks/secret-scan.sh
assert_file_exists .claude/hooks/check-doc-sync.sh
assert_executable .claude/hooks/check-doc-sync.sh
assert_file_exists .claude/hooks/notify.sh

# settings.json must reference all three hooks
for h in session-context secret-scan check-doc-sync; do
    if grep -q "$h.sh" .claude/settings.json 2>/dev/null; then
        pass "hook $h registered in settings.json"
    else
        fail "hook $h registered in settings.json" "not found"
    fi
done

# git hooks (commit-msg, pre-push) should exist
assert_file_exists .git/hooks/commit-msg
assert_executable .git/hooks/commit-msg
assert_file_exists .git/hooks/pre-push
