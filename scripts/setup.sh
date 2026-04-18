#!/bin/bash
# Project setup for new developers.
# Safe to re-run.

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==> Checking Python version"
python3 -c "import sys; assert sys.version_info >= (3, 9), 'Python 3.9+ required'"
python3 --version

echo ""
echo "==> Installing dependencies"
pip install --user -r requirements.txt

echo ""
echo "==> Setting up .env.local"
if [ ! -f .env.local ]; then
    if [ -f .env.local.example ]; then
        cp .env.local.example .env.local
        chmod 600 .env.local
        echo "Created .env.local from template. Edit it with your credentials:"
        echo "  - AWS_BEARER_TOKEN_BEDROCK (or use AWS_PROFILE/IAM role)"
        echo "  - AWS_REGION=us-east-1"
        echo "  - ANTHROPIC_API_KEY (optional, for 1P tests)"
    else
        echo "WARN: .env.local.example not found"
    fi
else
    echo "  .env.local already exists (not overwriting)"
fi

echo ""
echo "==> Verifying imports"
python3 -c "import anthropic, boto3, botocore, requests, rich, dotenv, pytest; print('All imports OK')"

echo ""
echo "==> Running unit tests"
python3 -m pytest tests/ -q

echo ""
echo "==> Dry-run benchmark (no API calls)"
python3 run.py --dry-run --test 1 --runs 1

echo ""
echo "Setup complete."
echo ""
echo "Next steps:"
echo "  1. Edit .env.local with real credentials"
echo "  2. Run a real benchmark:  python3 run.py --test 1 --runs 1"
echo "  3. See docs/onboarding.md for more"
