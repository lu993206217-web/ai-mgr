#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_DIR}"

if [[ -f /opt/ai-mgr/runtime/data/app.db ]]; then
  bash deploy/backup.sh
fi
git pull --ff-only
bash deploy/deploy.sh
