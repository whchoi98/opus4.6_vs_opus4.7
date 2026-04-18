#!/bin/bash
# PostToolUse hook — after Write/Edit, checks whether the modified file has
# a matching CLAUDE.md in its module directory. Warns (does not block) if missing.

set +e

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$PROJECT_ROOT" || exit 0

# Extract file_path from tool input (stdin is JSON)
INPUT="$(cat)"
FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
    print(d.get('tool_input', {}).get('file_path', ''))
except Exception:
    pass
" 2>/dev/null)

[ -z "$FILE_PATH" ] && exit 0

# Normalize to project-relative
REL_PATH="${FILE_PATH#$PROJECT_ROOT/}"

# Only check for our Python source directories
case "$REL_PATH" in
  clients/*|cases/*|runner/*|scorers/*)
    ;;
  *)
    exit 0
    ;;
esac

# Walk up to find CLAUDE.md
DIR="$(dirname "$REL_PATH")"
while [ "$DIR" != "." ] && [ "$DIR" != "/" ]; do
  if [ -f "$DIR/CLAUDE.md" ]; then
    exit 0
  fi
  DIR="$(dirname "$DIR")"
done

# Top-level CLAUDE.md should exist
if [ -f CLAUDE.md ]; then
  MODULE_DIR="$(echo "$REL_PATH" | cut -d/ -f1)"
  if [ ! -f "$MODULE_DIR/CLAUDE.md" ]; then
    echo "Note: $MODULE_DIR/ lacks CLAUDE.md. Consider documenting module role." >&2
  fi
fi

exit 0
