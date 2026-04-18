#!/bin/bash
# Install git hooks — specifically a commit-msg hook that strips Co-Authored-By lines
# and a pre-push check that runs pytest.

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [ ! -d .git ]; then
    echo "Not a git repo. Run 'git init' first."
    exit 1
fi

mkdir -p .git/hooks

cat > .git/hooks/commit-msg << 'EOF'
#!/bin/bash
# Strips Co-Authored-By lines (any case) from commit messages.
# Keeps AI assistants (Claude, Copilot, etc.) out of the contributor list.
MSG_FILE="$1"
grep -iv '^co-authored-by:' "$MSG_FILE" > "$MSG_FILE.tmp" && mv "$MSG_FILE.tmp" "$MSG_FILE"
exit 0
EOF
chmod +x .git/hooks/commit-msg
echo "Installed: commit-msg (strips Co-Authored-By lines, case-insensitive)"

cat > .git/hooks/pre-push << 'EOF'
#!/bin/bash
# Pre-push: run unit tests. Don't push broken code.
cd "$(git rev-parse --show-toplevel)"
echo "Running pytest before push..."
if ! python3 -m pytest tests/ -q; then
    echo ""
    echo "Tests failed. Push aborted. Use 'git push --no-verify' to skip."
    exit 1
fi
exit 0
EOF
chmod +x .git/hooks/pre-push
echo "Installed: pre-push (runs pytest)"

echo ""
echo "Git hooks installed. Test with:"
echo "  git commit --allow-empty -m 'test' -m 'Co-Authored-By: foo <foo@bar>'"
echo "  (the Co-Authored-By line should be stripped)"
