#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${1:-/opt/ai-mgr/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
TARGET="${BACKUP_DIR}/ai-mgr-runtime-${STAMP}.tar.gz"
RUNTIME_DIR="${AI_MGR_RUNTIME_DIR:-/opt/ai-mgr/runtime}"

if [[ ! -d "${RUNTIME_DIR}/data" && -d /var/lib/ai-mgr/data ]]; then
  RUNTIME_DIR="/var/lib/ai-mgr"
fi
if [[ ! -d "${RUNTIME_DIR}/data" ]]; then
  echo "未找到运行数据目录：${RUNTIME_DIR}/data"
  exit 1
fi

install -d -m 750 "${BACKUP_DIR}"
tar -czf "${TARGET}" -C "${RUNTIME_DIR}" data uploads
chmod 600 "${TARGET}"
echo "备份完成：${TARGET}"
