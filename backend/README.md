# AI 项目推进控制塔

AI Project Control Tower - 让项目不丢失、不卡死、渠道资产沉淀。

---

## 📋 项目结构

```
ai-control-tower/
├── backend/               # 后端（FastAPI + PostgreSQL）
│   ├── app/
│   │   ├── api/v1/      # API 路由
│   │   ├── models/       # ORM 模型
│   │   ├── schemas/      # Pydantic Schema
│   │   ├── services/     # 业务逻辑
│   │   ├── core/         # 核心配置
│   │   └── db/          # 数据库连接
│   ├── requirements.txt
│   ├── run.py           # 启动脚本
│   └── .env             # 环境配置
├── frontend/             # 前端（Vue 3 + TypeScript）
└── deploy/              # 部署配置
```

---

## 🚀 快速启动（后端）

### 1. 安装依赖

```bash
cd /Users/lu/WorkBuddy/2026-06-13-10-50-39/ai-control-tower/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置数据库

**创建 PostgreSQL 数据库：**

```bash
# 登录 PostgreSQL
psql -U postgres

# 创建数据库
CREATE DATABASE ai_control_tower;

# 创建用户（可选）
CREATE USER ai_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE ai_control_tower TO ai_user;

# 退出
\q
```

**修改 `.env` 文件：**

```bash
# 编辑 .env 文件
vim .env

# 修改以下配置：
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ai_control_tower
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
```

### 3. 初始化数据库

```bash
# 创建表 + 初始数据（管理员账号 + 预警规则）
python run.py init-db
```

**初始账号：**
- 管理员：`admin` / `admin123`
- 测试用户：`test` / `test123`

### 4. 启动后端服务

```bash
# 开发模式（自动重载）
python run.py dev

# 或

# 生产模式（多进程）
python run.py prod
```

**访问地址：**
- API 文档：http://localhost:8000/api/docs
- ReDoc：http://localhost:8000/api/redoc
- 健康检查：http://localhost:8000/health

---

## 🧪 测试 API 接口

### 1. 登录获取 Token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

**响应示例：**
```json
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
}
```

### 2. 使用 Token 访问 API

```bash
# 获取当前用户信息
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 3. 创建项目

```bash
curl -X POST "http://localhost:8000/api/v1/projects" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "尼日利亚大学项目",
    "country": "尼日利亚",
    "customer_id": "CUSTOMER_UUID",
    "owner_id": "YOUR_USER_ID",
    "source_type": "渠道直转",
    "current_stage": "售前"
  }'
```

---

## 📚 API 文档

启动后端后，访问 Swagger 文档：
- **Swagger UI**：http://localhost:8000/api/docs
- **ReDoc**：http://localhost:8000/api/redoc

---

## 🎨 前端开发（待开始）

### 1. 初始化前端项目

```bash
cd /Users/lu/WorkBuddy/2026-06-13-10-50-39/ai-control-tower/frontend

# 使用 Vite 创建 Vue 3 + TypeScript 项目
npm create vite@latest . -- --template vue-ts

# 安装依赖
npm install

# 安装额外依赖
npm install tailwindcss @tailwindcss/vite vue-router pinia axios
```

### 2. 启动前端开发服务器

```bash
npm run dev
```

**访问地址：** http://localhost:5173

---

## 🛠️ 常用命令

```bash
# 重新初始化数据库（会删除所有数据！）
python run.py init-db

# 仅创建数据库表（不插入初始数据）
python run.py create-tables

# 启动调试模式（详细日志）
python run.py debug
```

---

## 📝 开发说明

### 后端技术栈
- **框架**：FastAPI 0.115.0
- **数据库**：PostgreSQL 16 + SQLAlchemy 2.0
- **认证**：JWT（python-jose + passlib）
- **迁移**：不使用 Alembic，直接使用 `Base.metadata.create_all()`

### 前端技术栈（规划）
- **框架**：Vue 3 + TypeScript
- **样式**：TailwindCSS
- **状态管理**：Pinia
- **路由**：Vue Router
- **HTTP 客户端**：Axios

---

## 🔧 遇到的问题？

### 1. 数据库连不上
- 检查 PostgreSQL 是否启动：`pg_isready`
- 检查 `.env` 配置是否正确
- 检查数据库和用户是否创建成功

### 2. 依赖安装失败
- 使用国内镜像：
  ```bash
  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  ```

### 3. 端口被占用
- 修改 `.env` 中的 `PORT` 配置
- 或杀掉占用进程：`lsof -i :8000 | kill -9 <PID>`

---

## 📞 联系方式

- **技术支持**：support@ai-control-tower.com
- **项目文档**：参见 `/Users/lu/WorkBuddy/2026-06-13-10-50-39/` 目录下的设计文档

---

## 📄 相关文档

- `PRD_V3.1_审批调整版.md` - 产品需求文档
- `database_schema.sql` - 数据库设计（SQL 版）
- `api_openapi.yaml` - API 接口设计（OpenAPI 3.0）
- `CLAUDE.md` - 开发规范
- `deployment_design.md` - 部署架构设计
- `deepseek_integration_design.md` - DeepSeek 集成设计
