#!/usr/bin/env bash
# Run the agency content pipeline with the sample brief.
# Make sure .env is configured first: python -m src.config

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Load WP_SITE_URL from .env if not already set
if [ -z "$WP_SITE_URL" ]; then
    WP_SITE_URL=$(grep '^WP_SITE_URL=' .env | cut -d '=' -f2-)
fi

if [ -z "$WP_SITE_URL" ]; then
    echo "Error: WP_SITE_URL not found in .env or environment."
    echo "Run: python -m src.config"
    exit 1
fi

echo "=== Agency Content Pipeline ==="
echo "Brief:  examples/sample_brief.md"
echo "Target: $WP_SITE_URL"
echo ""

python -m src.graph \
    --brief examples/sample_brief.md \
    --wp-url "$WP_SITE_URL"
