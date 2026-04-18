#!/bin/bash
# PreToolUse hook — blocks Bash commands that embed secrets inline.
# Exits non-zero to block tool use. Does NOT inspect file contents.

set +e

INPUT="$(cat)"

# Patterns of secrets embedded in command args (not just references to env files)
# Be conservative — too many false positives is worse than missing some signal.

# Anthropic API key pattern — 108 chars starting with sk-ant-
if echo "$INPUT" | grep -qE 'sk-ant-api[0-9]{2,}-[A-Za-z0-9_-]{80,}'; then
  echo "BLOCKED: Command contains inline Anthropic API key. Use \$ANTHROPIC_API_KEY env var instead." >&2
  exit 1
fi

# Bedrock API key pattern — starts with ABSK, base64-like suffix
if echo "$INPUT" | grep -qE 'ABSK[A-Za-z0-9+/=]{100,}'; then
  echo "BLOCKED: Command contains inline Bedrock API key. Use \$AWS_BEARER_TOKEN_BEDROCK env var instead." >&2
  exit 1
fi

# AWS access key ID (20 chars starting AKIA or ASIA)
if echo "$INPUT" | grep -qE '\b(AKIA|ASIA)[A-Z0-9]{16}\b'; then
  echo "BLOCKED: Command contains inline AWS access key. Use AWS_PROFILE or IAM role instead." >&2
  exit 1
fi

# AWS secret access key — 40 chars base64-like, preceded by 'aws_secret' or 'SECRET'
if echo "$INPUT" | grep -qE 'aws_secret_access_key\s*=\s*["'\'']?[A-Za-z0-9/+=]{40}'; then
  echo "BLOCKED: Command contains inline AWS secret key." >&2
  exit 1
fi

exit 0
