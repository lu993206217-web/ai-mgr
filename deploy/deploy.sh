#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.production"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "缺少 ${ENV_FILE}，请先复制 .env.production.example 并填写。"
  exit 1
fi

if grep -Eq '^(SECRET_KEY|INITIAL_ADMIN_PASSWORD)=replace-with-' "${ENV_FILE}"; then
  echo "生产配置仍包含示例密钥或密码，拒绝部署。"
  exit 1
fi

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
  else
    echo "未找到 Docker Compose"
    exit 1
  fi
}

cd "${PROJECT_DIR}"
install -d -m 750 /opt/ai-mgr/runtime/data /opt/ai-mgr/runtime/uploads
WEB_PORT_VALUE="$(sed -n 's/^WEB_PORT=//p' "${ENV_FILE}" | tail -1)"
WEB_PORT_VALUE="${WEB_PORT_VALUE:-80}"

echo "构建并启动服务..."
compose -f deploy/docker-compose.yml --env-file "${ENV_FILE}" up -d --build --remove-orphans

echo "等待健康检查..."
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${WEB_PORT_VALUE}/health" >/dev/null 2>&1; then
    echo "部署成功：http://服务器IP:${WEB_PORT_VALUE}"
    compose -f deploy/docker-compose.yml --env-file "${ENV_FILE}" ps
    exit 0
  fi
  sleep 2
done

echo "健康检查未通过，输出最近日志："
compose -f deploy/docker-compose.yml --env-file "${ENV_FILE}" logs --tail=120
exit 1
