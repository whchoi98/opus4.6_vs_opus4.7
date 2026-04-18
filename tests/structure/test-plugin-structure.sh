#!/bin/bash
# Validate key project files exist and have required sections.

# Manifests
assert_file_exists requirements.txt
assert_file_exists pyproject.toml
assert_file_exists .gitignore
assert_file_exists .mcp.json
assert_file_exists README.md
assert_file_exists CLAUDE.md

# Docs
assert_file_exists docs/architecture.md
assert_file_exists docs/onboarding.md
assert_file_exists docs/decisions/.template.md
assert_file_exists docs/runbooks/.template.md

# Skills
assert_file_exists .claude/skills/code-review/SKILL.md
assert_file_exists .claude/skills/refactor/SKILL.md
assert_file_exists .claude/skills/release/SKILL.md
assert_file_exists .claude/skills/sync-docs/SKILL.md

# Commands
assert_file_exists .claude/commands/review.md
assert_file_exists .claude/commands/test-all.md
assert_file_exists .claude/commands/deploy.md

# Agents
assert_file_exists .claude/agents/code-reviewer.yml
assert_file_exists .claude/agents/security-auditor.yml

# Module CLAUDE.md files
for mod in clients cases runner scorers tests; do
    assert_file_exists "$mod/CLAUDE.md"
done

# Settings
assert_file_exists .claude/settings.json

# Settings.json must not contain real secrets
assert_pattern_not_found "sk-ant-api03" .claude/settings.json "no anthropic key in settings"
assert_pattern_not_found "ABSKQm" .claude/settings.json "no bedrock key in settings"

# README links to key docs
for link in architecture.md onboarding.md findings; do
    if grep -q "$link" README.md 2>/dev/null; then
        pass "README references $link"
    else
        fail "README references $link" "missing link"
    fi
done
