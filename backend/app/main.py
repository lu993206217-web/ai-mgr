"""
FastAPI 主应用

AI 项目推进控制塔系统入口。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_422_UNPROCESSABLE_ENTITY

from app.core.config import settings
from app.db.session import init_db, Base
from app.api.v1 import auth, projects, activities, channels, customers, quotes, warnings, dashboard, users, config


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    description="AI 项目推进控制塔 - 让项目不丢失、不卡死、渠道资产沉淀",
    version=settings.APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    redirect_slashes=False,
    contact={
        "name": "AI Control Tower Team",
        "email": "support@ai-control-tower.com",
    },
)


# ============ CORS 中间件 ============
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ 全局异常处理 ============
@app.exception_handler(HTTP_401_UNAUTHORIZED)
async def unauthorized_handler(request, exc):
    """401 未认证"""
    return JSONResponse(
        status_code=HTTP_401_UNAUTHORIZED,
        content={
            "code": 401,
            "message": "未认证，请先登录",
            "data": None,
        },
    )


@app.exception_handler(HTTP_403_FORBIDDEN)
async def forbidden_handler(request, exc):
    """403 无权限"""
    return JSONResponse(
        status_code=HTTP_403_FORBIDDEN,
        content={
            "code": 403,
            "message": "无权限访问此资源",
            "data": None,
        },
    )


@app.exception_handler(HTTP_404_NOT_FOUND)
async def not_found_handler(request, exc):
    """404 资源不存在"""
    return JSONResponse(
        status_code=HTTP_404_NOT_FOUND,
        content={
            "code": 404,
            "message": "请求的资源不存在",
            "data": None,
        },
    )


@app.exception_handler(HTTP_500_INTERNAL_SERVER_ERROR)
async def internal_error_handler(request, exc):
    """500 内部服务器错误"""
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "服务器内部错误，请联系管理员",
            "data": None,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    """422 验证错误"""
    # 解析Pydantic验证错误
    error_messages = []
    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"])
        msg = error["msg"]
        error_messages.append(f"{field}: {msg}")
    
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": 422,
            "message": "; ".join(error_messages) if error_messages else "请求参数验证失败",
            "data": None,
        },
    )


# ============ 健康检查接口 ============
@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
    }


# ============ API 路由注册 ============
api_v1_prefix = "/api/v1"

app.include_router(auth.router, prefix=api_v1_prefix + "/auth")
app.include_router(users.router, prefix=api_v1_prefix + "/users", dependencies=[])
app.include_router(projects.router, prefix=api_v1_prefix + "/projects", dependencies=[])
app.include_router(activities.router, prefix=api_v1_prefix + "/activities", dependencies=[])
app.include_router(channels.router, prefix=api_v1_prefix + "/channels", dependencies=[])
app.include_router(customers.router, prefix=api_v1_prefix + "/customers", dependencies=[])
app.include_router(quotes.router, prefix=api_v1_prefix + "/quotes", dependencies=[])
app.include_router(warnings.router, prefix=api_v1_prefix + "/warnings", dependencies=[])
app.include_router(dashboard.router, prefix=api_v1_prefix + "/dashboard", dependencies=[])
app.include_router(config.router, prefix=api_v1_prefix + "/config", dependencies=[])


# ============ 启动事件 ============
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    # 初始化数据库表
    init_db()
    print(f"✅ {settings.APP_NAME} v{settings.APP_VERSION} 启动成功")
    print(f"📝 API 文档地址: http://{settings.HOST}:{settings.PORT}/api/docs")
    print(f"🔧 调试模式: {'开启' if settings.DEBUG else '关闭'}")

    # 种子数据：创建默认管理员
    _seed_admin_user()


def _seed_admin_user():
    """创建默认管理员用户（如果不存在）"""
    from app.db.session import SessionLocal
    from app.models.user import User
    from app.core.security import get_password_hash

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if not existing:
            admin_user = User(
                username="admin",
                email="admin@ai-control-tower.com",
                full_name="系统管理员",
                hashed_password=get_password_hash("admin123"),
                role="管理员",
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            print("👤 默认管理员账户已创建: admin / admin123")
        else:
            print("👤 管理员账户已存在: admin")
    except Exception as e:
        print(f"⚠️ 创建管理员失败: {e}")
    finally:
        db.close()


# ============ 关闭事件 ============
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    print(f"👋 {settings.APP_NAME} 已关闭")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
