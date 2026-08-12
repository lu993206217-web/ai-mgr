#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${1:-/opt/ai-mgr/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
TARGET="${BACKUP_DIR}/ai-mgr-runtime-${STAMP}.tar.gz"

install -d -m 750 "${BACKUP_DIR}"
tar -czf "${TARGET}" -C /opt/ai-mgr/runtime data uploads
chmod 600 "${TARGET}"
echo "备份完成：${TARGET}"
