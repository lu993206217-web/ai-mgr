#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "请使用root执行本脚本"
  exit 1
fi

NODE_VERSION="20.19.5"
ARCH="$(uname -m)"
case "${ARCH}" in
  x86_64) NODE_ARCH="x64" ;;
  aarch64) NODE_ARCH="arm64" ;;
  *) echo "不支持的CPU架构：${ARCH}"; exit 1 ;;
esac

echo "[1/7] 安装系统依赖"
dnf install -y git curl tar xz nginx python3 python3-pip python3-devel gcc gcc-c++ openssl-devel libffi-devel policycoreutils-python-utils firewalld

echo "[2/7] 安装Node.js ${NODE_VERSION}"
CURRENT_NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
if (( CURRENT_NODE_MAJOR < 18 )); then
  NODE_TARBALL="node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz"
  curl -fL "https://nodejs.org/dist/v${NODE_VERSION}/${NODE_TARBALL}" -o "/tmp/${NODE_TARBALL}"
  tar -xJf "/tmp/${NODE_TARBALL}" -C /opt
  ln -sfn "/opt/node-v${NODE_VERSION}-linux-${NODE_ARCH}" /opt/node
  ln -sfn /opt/node/bin/node /usr/local/bin/node
  ln -sfn /opt/node/bin/npm /usr/local/bin/npm
  ln -sfn /opt/node/bin/npx /usr/local/bin/npx
fi

echo "[3/7] 创建服务账户和目录"
id ai-mgr >/dev/null 2>&1 || useradd --system --home-dir /opt/ai-mgr --shell /sbin/nologin ai-mgr
install -d -o ai-mgr -g ai-mgr -m 750 /opt/ai-mgr /var/lib/ai-mgr/data /var/lib/ai-mgr/uploads /var/log/ai-mgr
install -d -o root -g ai-mgr -m 750 /etc/ai-mgr

echo "[4/7] 获取代码"
if [[ -d /opt/ai-mgr/app/.git ]]; then
  runuser -u ai-mgr -- git -C /opt/ai-mgr/app pull --ff-only
else
  git clone https://github.com/lu993206217-web/ai-mgr.git /opt/ai-mgr/app
fi
chown -R ai-mgr:ai-mgr /opt/ai-mgr/app

echo "[5/7] 准备运行数据目录"
if [[ -e /opt/ai-mgr/app/backend/data && ! -L /opt/ai-mgr/app/backend/data ]]; then
  cp -a /opt/ai-mgr/app/backend/data/. /var/lib/ai-mgr/data/
  mv /opt/ai-mgr/app/backend/data "/opt/ai-mgr/app/backend/data.pre-native.$(date +%s)"
fi
ln -sfn /var/lib/ai-mgr/data /opt/ai-mgr/app/backend/data
chown -h ai-mgr:ai-mgr /opt/ai-mgr/app/backend/data
chown -R ai-mgr:ai-mgr /var/lib/ai-mgr

echo "[6/7] 安装systemd和Nginx配置"
install -m 644 /opt/ai-mgr/app/deploy/native/ai-mgr.service /etc/systemd/system/ai-mgr.service
install -m 644 /opt/ai-mgr/app/deploy/native/nginx-ai-mgr.conf /etc/nginx/conf.d/ai-mgr.conf
if [[ -f /etc/nginx/conf.d/default.conf ]]; then
  mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.disabled
fi
# openEuler的Nginx软件包会把默认站点直接写在nginx.conf中。将它移到
# 本机8080端口，避免与AI项目情报平台的80端口默认站点冲突。
if grep -Eq '^[[:space:]]*listen[[:space:]]+80;' /etc/nginx/nginx.conf; then
  sed -i 's/^[[:space:]]*listen[[:space:]]\+80;/        listen       127.0.0.1:8080;/' /etc/nginx/nginx.conf
fi
if grep -Eq '^[[:space:]]*listen[[:space:]]+\[::\]:80;' /etc/nginx/nginx.conf; then
  sed -i 's/^[[:space:]]*listen[[:space:]]\+\[::\]:80;/        # IPv6 default site disabled; AI project listens on port 80./' /etc/nginx/nginx.conf
fi
setsebool -P httpd_can_network_connect 1
semanage fcontext -a -t httpd_sys_content_t '/usr/share/nginx/html/ai-mgr(/.*)?' 2>/dev/null || semanage fcontext -m -t httpd_sys_content_t '/usr/share/nginx/html/ai-mgr(/.*)?'
systemctl daemon-reload
systemctl enable nginx ai-mgr
systemctl enable --now firewalld
firewall-cmd --permanent --add-service=http
firewall-cmd --reload

echo "[7/7] 准备生产配置"
if [[ ! -f /etc/ai-mgr/ai-mgr.env ]]; then
  cp /opt/ai-mgr/app/deploy/.env.production.example /etc/ai-mgr/ai-mgr.env
  chmod 640 /etc/ai-mgr/ai-mgr.env
  chown root:ai-mgr /etc/ai-mgr/ai-mgr.env
fi

echo "基础环境完成。填写 /etc/ai-mgr/ai-mgr.env 后执行：bash /opt/ai-mgr/app/deploy/native/deploy.sh"
