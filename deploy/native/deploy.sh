#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "请使用root执行本脚本"
  exit 1
fi

APP_ROOT="/opt/ai-mgr/app"
ENV_FILE="/etc/ai-mgr/ai-mgr.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "缺少生产配置：${ENV_FILE}"
  exit 1
fi
if grep -Eq '^(SECRET_KEY|INITIAL_ADMIN_PASSWORD)=replace-with-' "${ENV_FILE}"; then
  echo "生产配置仍包含示例密钥或密码，拒绝启动"
  exit 1
fi

echo "[1/5] 安装后端依赖"
python3 -m venv /opt/ai-mgr/venv
/opt/ai-mgr/venv/bin/python -m pip install --upgrade pip wheel
/opt/ai-mgr/venv/bin/pip install -r "${APP_ROOT}/backend/requirements.txt"

echo "[2/5] 初始化或升级SQLite表"
set -a
source "${ENV_FILE}"
set +a
cd "${APP_ROOT}/backend"
runuser -u ai-mgr --preserve-environment -- /opt/ai-mgr/venv/bin/python "${APP_ROOT}/backend/run.py" create-tables

echo "[3/5] 构建前端"
cd "${APP_ROOT}/frontend"
/usr/local/bin/npm ci
/usr/local/bin/npm run build
install -d -m 755 /usr/share/nginx/html/ai-mgr
find /usr/share/nginx/html/ai-mgr -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
cp -a dist/. /usr/share/nginx/html/ai-mgr/
restorecon -RF /usr/share/nginx/html/ai-mgr

echo "[4/5] 启动服务"
nginx -t
systemctl restart ai-mgr
systemctl restart nginx

echo "[5/5] 健康检查"
for _ in $(seq 1 40); do
  if curl -fsS http://127.0.0.1/health >/dev/null; then
    systemctl --no-pager --full status ai-mgr nginx | head -40
    echo "部署成功：http://$(hostname -I | awk '{print $1}')/"
    exit 0
  fi
  sleep 2
done

journalctl -u ai-mgr --no-pager -n 120
exit 1
