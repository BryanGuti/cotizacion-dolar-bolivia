#!/usr/bin/env bash
set -euo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPOSITORY_ROOT"

umask 077
mkdir -p logs
chmod 700 logs
LOG_FILE="logs/$(date +%F).log"
touch "$LOG_FILE"
chmod 600 "$LOG_FILE"
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
    if [[ -S "$KEYRING_SSH_SOCKET" && -O "$KEYRING_SSH_SOCKET" ]]; then
        export SSH_AUTH_SOCK="$KEYRING_SSH_SOCKET"
        echo "Using the SSH agent socket from GNOME Keyring."
    fi
fi

source .venv/bin/activate
SCRAPER_STATUS=0
if python -m scraper.main; then
    :
else
    SCRAPER_STATUS=$?
fi

if [[ "$SCRAPER_STATUS" -ne 0 ]]; then
    echo "El scraper terminó con errores (código $SCRAPER_STATUS); se continuará con la actualización de GitHub."
fi

DATA_CHANGES="$(git status --porcelain -- frontend/data/)"
if [[ -n "$DATA_CHANGES" ]]; then
    git add -- frontend/
    if git diff --cached --quiet -- frontend/; then
        echo "No stageable frontend changes; skipping commit and push."
    else
        git commit -m "Update Data ($(date '+%Y-%m-%d %H:%M:%S'))" -- frontend/
        git push
        echo "Frontend changes committed and pushed."
    fi
else
    echo "No frontend/data changes; skipping add, commit, and push."
fi

exit "$SCRAPER_STATUS"
