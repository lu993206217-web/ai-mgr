#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "请使用 root 执行：sudo bash deploy/setup-openeuler22.sh"
  exit 1
fi

echo "[1/4] 安装 Git、Docker 和 Docker Compose"
dnf install -y git curl docker docker-compose

echo "[2/4] 启动 Docker"
systemctl enable --now docker

echo "[3/4] 创建持久化目录"
install -d -m 750 /opt/ai-mgr/runtime/data /opt/ai-mgr/runtime/uploads

echo "[4/4] 准备生产配置"
if [[ ! -f deploy/.env.production ]]; then
  cp deploy/.env.production.example deploy/.env.production
  chmod 600 deploy/.env.production
  echo "已生成 deploy/.env.production，请先填写服务器IP、强密码和各接口密钥。"
else
  chmod 600 deploy/.env.production
  echo "已保留现有 deploy/.env.production。"
fi

echo
echo "环境准备完成。填写配置后执行：bash deploy/deploy.sh"
