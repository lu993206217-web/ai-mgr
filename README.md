# AI项目情报平台

面向海外项目的AI项目情报与推进控制塔。系统自动采集日报和邮件，保留原始事实，通过AI完成项目匹配、摘要、行动项和风险分析，并由流程中心持续推进、分级告警与人工确认闭环。

## 本地开发

后端：

```bash
cd backend
cp .env.example .env
PORT=8001 python3 run.py dev
```

前端：

```bash
cd frontend
npm ci
npm run dev -- --host 0.0.0.0 --port 3001
```

访问`http://127.0.0.1:3001`。

## openEuler 22.03部署

当前推荐原生部署：Nginx、Python虚拟环境、systemd、单进程FastAPI和持久化SQLite，不依赖容器。完整步骤见：

- [openEuler 22.03部署手册](docs/OPEN_EULER_22_DEPLOYMENT.md)
- [生产环境变量模板](deploy/.env.production.example)

服务器初始化：

```bash
sudo bash deploy/native/setup-openeuler22.sh
sudo vi /etc/ai-mgr/ai-mgr.env
sudo bash deploy/native/deploy.sh
```

## 数据安全

以下内容不会进入Git：

- `.env`和生产密钥
- SQLite数据库
- 邮件原文与附件
- 邮箱客户端专用密码
- 消息渠道Token
- 本地备份

本地业务数据需要迁移时，请使用`scripts/export-runtime-data.sh`生成加密传输范围内的临时包，并通过`scp`等安全通道传输。
