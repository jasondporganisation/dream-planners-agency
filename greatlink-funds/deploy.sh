#!/usr/bin/env bash
# Post-refresh deploy: commit updated data to GitHub → Vercel auto-deploys from main.
# Called by cron immediately after refresh.py succeeds.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
LOGFILE="$REPO_DIR/deploy.log"
export HOME="/Users/jasonng"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S')  $*" | tee -a "$LOGFILE"; }

log "=== deploy.sh started ==="

# Stage only the files refresh.py writes
git -C "$REPO_DIR" add \
  dashboard.html \
  data/funds.json \
  data/funds.csv \
  data/refresh_report.md

if git -C "$REPO_DIR" diff --cached --quiet; then
  log "Nothing changed — skipping commit."
  exit 0
fi

DATE_LABEL=$(date +'%d %b %Y')
git -C "$REPO_DIR" commit -m "Refresh GreatLink fund data (as at $DATE_LABEL)"
git -C "$REPO_DIR" push origin HEAD:main
log "Pushed to GitHub — Vercel will auto-deploy."

log "=== deploy.sh done ==="
