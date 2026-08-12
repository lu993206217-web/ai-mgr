#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT="${1:-${PROJECT_DIR}/ai-mgr-runtime-$(date +%Y%m%d-%H%M%S).tar.gz}"

if [[ ! -f "${PROJECT_DIR}/backend/data/app.db" ]]; then
  echo "未找到 backend/data/app.db"
  exit 1
fi

echo "正在导出SQLite、邮件原文和附件；不会包含邮箱密码或消息渠道Token。"
tar \
  --exclude='data/mail_credentials.json' \
  --exclude='data/message_center_config.json' \
  -czf "${OUTPUT}" \
  -C "${PROJECT_DIR}/backend" data
chmod 600 "${OUTPUT}"
echo "导出完成：${OUTPUT}"
echo "该文件包含业务与邮件数据，请通过 scp 等安全方式传输，不要上传GitHub。"
