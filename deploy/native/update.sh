#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "请使用root执行本脚本"
  exit 1
fi

bash /opt/ai-mgr/app/deploy/backup.sh /opt/ai-mgr/backups
git -C /opt/ai-mgr/app pull --ff-only
bash /opt/ai-mgr/app/deploy/native/deploy.sh
