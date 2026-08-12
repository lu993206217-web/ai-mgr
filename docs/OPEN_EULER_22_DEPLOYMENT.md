# AI项目情报平台：openEuler 22.03 部署手册

## 1. 部署边界

- GitHub只保存源代码、依赖锁定文件和部署模板。
- SQLite、邮件原文、附件、邮箱第三方安全密码、DeepSeek Key、日报Key、消息渠道Token不进入GitHub。
- 生产后端固定为单进程。原因是当前使用SQLite，且自动推进调度器位于后端进程内；多进程会造成重复拉取和并发写库。
- 前端Nginx统一提供页面和反向代理，外部只需开放一个Web端口。

## 2. 服务器要求

- openEuler 22.03 LTS/SP版本，x86_64或AArch64。
- 建议至少2核CPU、4 GB内存、20 GB可用磁盘；若迁移邮件附件，应根据附件量扩大磁盘。
- 服务器能访问GitHub、Python/Node容器镜像、DeepSeek、企业邮箱IMAP，以及局域网日报接口。
- openEuler官方文档说明22.03提供Docker容器引擎，可通过`dnf/yum`安装Docker；本项目同时兼容`docker compose`和`docker-compose`。

## 3. 首次部署

```bash
sudo mkdir -p /opt/ai-mgr
sudo chown "$USER":"$USER" /opt/ai-mgr
git clone https://github.com/lu993206217-web/ai-mgr.git /opt/ai-mgr/app
cd /opt/ai-mgr/app
sudo bash deploy/setup-openeuler22.sh
```

编辑生产配置：

```bash
sudo vi deploy/.env.production
```

必须修改：

- `SECRET_KEY`：至少32位随机字符串，可用`openssl rand -hex 32`生成。
- `INITIAL_ADMIN_PASSWORD`：初始管理员强密码，禁止使用`admin123`。
- `ALLOWED_ORIGINS`：改为实际服务器IP或域名。
- `DEEPSEEK_API_KEY`、`DAILY_REPORT_API_KEY`：按实际配置。
- `DAILY_REPORT_API_BASE_URL`：确认openEuler服务器能访问该局域网地址。
- 邮箱密码建议先留空，登录系统后在邮件情报页面配置第三方安全密码。

启动：

```bash
sudo bash deploy/deploy.sh
```

默认访问：`http://服务器IP/`。

若启用了防火墙：

```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --reload
```

## 4. 迁移当前本地测试数据（可选）

数据包含邮件原文和附件，禁止通过GitHub迁移。

在Mac项目目录执行：

```bash
bash scripts/export-runtime-data.sh
scp ai-mgr-runtime-*.tar.gz root@服务器IP:/opt/ai-mgr/
```

在openEuler服务器执行：

```bash
cd /opt/ai-mgr
sudo tar -xzf ai-mgr-runtime-*.tar.gz -C /opt/ai-mgr/runtime
sudo chmod -R o-rwx /opt/ai-mgr/runtime
sudo bash /opt/ai-mgr/app/deploy/deploy.sh
```

导出包默认不包含邮箱密码和消息渠道Token，迁移后需在页面重新配置。

## 5. 验收清单

```bash
cd /opt/ai-mgr/app
docker ps
curl -f http://127.0.0.1/health
docker-compose -f deploy/docker-compose.yml --env-file deploy/.env.production logs --tail=100 backend
```

浏览器验收：

1. 使用配置的初始管理员登录，并立即修改密码。
2. 打开项目、流程中心、告警中心，确认列表正常。
3. 在邮件情报中测试IMAP/SMTP连接，手工同步一轮。
4. 在日报导入中同步最近一天，确认原始数据先落库、低可信不自动导入。
5. 在流程中心确认自动任务周期、运行记录和告警复核结果。
6. 重启容器，确认SQLite数据、邮件原文和附件仍存在。

## 6. 更新与回滚

更新前自动备份运行数据，然后拉取代码并重建：

```bash
cd /opt/ai-mgr/app
sudo bash deploy/update.sh
```

手工备份：

```bash
sudo bash deploy/backup.sh
```

备份默认保存在`/opt/ai-mgr/backups`。发生问题时，停止容器，将对应备份解压回`/opt/ai-mgr/runtime`后重新执行部署脚本。

## 7. 常用运维命令

```bash
cd /opt/ai-mgr/app
docker-compose -f deploy/docker-compose.yml --env-file deploy/.env.production ps
docker-compose -f deploy/docker-compose.yml --env-file deploy/.env.production logs -f --tail=200
docker-compose -f deploy/docker-compose.yml --env-file deploy/.env.production restart backend
docker-compose -f deploy/docker-compose.yml --env-file deploy/.env.production down
```

若服务器使用新版Compose，将`docker-compose`替换为`docker compose`。
