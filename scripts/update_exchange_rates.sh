#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPOSITORY_ROOT"

mkdir -p logs
LOG_FILE="logs/$(date +%F).log"
exec >>"$LOG_FILE" 2>&1

RUN_START="$(date '+%Y-%m-%d %H:%M:%S %Z')"
finish_run() {
    status=$?
    trap - EXIT
    printf '\n===== RUN END   %s | pid=%s | exit_status=%s =====\n\n' \
        "$(date '+%Y-%m-%d %H:%M:%S %Z')" "$$" "$status"
    exit "$status"
}
trap finish_run EXIT

printf '\n\n===== RUN START %s | pid=%s =====\n' "$RUN_START" "$$"

source .venv/bin/activate
python -m scraper.main

git add -- frontend/
if git diff --cached --quiet -- frontend/; then
    echo "No frontend changes; nothing to commit."
    exit 0
fi

git commit -m "Update Data ($(date '+%Y-%m-%d %H:%M:%S'))" -- frontend/
git push
echo "Update committed and pushed."
