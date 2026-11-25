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

# Cron does not inherit the GNOME Keyring SSH agent socket from the desktop.
if [[ -z "${SSH_AUTH_SOCK:-}" ]]; then
    KEYRING_SSH_SOCKET="/run/user/$(id -u)/keyring/ssh"
    if [[ -S "$KEYRING_SSH_SOCKET" ]]; then
        export SSH_AUTH_SOCK="$KEYRING_SSH_SOCKET"
        echo "Using the SSH agent socket from GNOME Keyring."
    fi
fi

source .venv/bin/activate
python -m scraper.main

git add -- frontend/
if git diff --cached --quiet -- frontend/; then
    echo "No frontend changes; nothing to commit."
else
    git commit -m "Update Data ($(date '+%Y-%m-%d %H:%M:%S'))" -- frontend/
fi

# Push even when this run made no new commit, so a previous failed push retries.
git push
echo "Update committed and pushed."
