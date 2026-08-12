"""
FastAPI 主应用

AI 项目推进控制塔系统入口。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR, HTTP_422_UNPROCESSABLE_ENTITY
from datetime import datetime, timedelta
import threading
import time
from zoneinfo import ZoneInfo
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
except ModuleNotFoundError:
    BackgroundScheduler = None
    CronTrigger = None

from app.core.config import settings
from app.db.session import init_db, Base
from app.api.v1 import auth, projects, activities, channels, customers, quotes, warnings, dashboard, users, config, daily_reports, email_intelligence, message_linkage, overseas_performance, workflow_center


scheduler = BackgroundScheduler(timezone="Asia/Shanghai") if BackgroundScheduler else None
fallback_scheduler = None


class DailyFallbackScheduler:
    """APScheduler 不可用时的每日定时兜底。"""

    def __init__(self, hour: int, minute: int, job):
        self.hour = hour
        self.minute = minute
        self.job = job
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self.running = False

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread.start()

    def shutdown(self, wait: bool = False):
        self._stop_event.set()
        self.running = False
        if wait:
            self._thread.join(timeout=5)

    def _run(self):
        timezone = ZoneInfo("Asia/Shanghai")
        while not self._stop_event.is_set():
            now = datetime.now(timezone)
            next_run = now.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
            wait_seconds = max(1, int((next_run - now).total_seconds()))
            if self._stop_event.wait(wait_seconds):
                break
            try:
                self.job()
            except Exception as e:
                print(f"⚠️ 兜底日报同步任务失败: {e}")


class IntervalFallbackScheduler:
    """无需第三方调度组件的固定间隔兜底任务。"""

    def __init__(self, seconds: int, job, initial_delay: int = 5):
        self.seconds = max(10, seconds)
        self.job = job
        self.initial_delay = max(1, initial_delay)
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self.running = False

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread.start()

    def shutdown(self, wait: bool = False):
        self._stop_event.set()
        self.running = False
        if wait:
            self._thread.join(timeout=5)

    def _run(self):
        if self._stop_event.wait(self.initial_delay):
            return
        while not self._stop_event.is_set():
            try:
                self.job()
            except Exception as exc:
                print(f"⚠️ 自动推进兜底调度失败: {exc}")
            if self._stop_event.wait(self.seconds):
                break


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
app.include_router(daily_reports.router, prefix=api_v1_prefix + "/daily-reports", dependencies=[])
app.include_router(email_intelligence.router, prefix=api_v1_prefix + "/email-intelligence", dependencies=[])
app.include_router(message_linkage.router, prefix=api_v1_prefix + "/message-linkage", dependencies=[])
app.include_router(overseas_performance.router, prefix=api_v1_prefix + "/overseas-performance", dependencies=[])
app.include_router(workflow_center.router, prefix=api_v1_prefix + "/workflow-center", dependencies=[])


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
    _start_workflow_automation_scheduler()
    _start_intelligence_snapshot_scheduler()
    _start_overseas_performance_scheduler()


def _seed_admin_user():
    """创建默认管理员用户（如果不存在）"""
    from app.db.session import SessionLocal
    from app.models.user import User
    from app.core.security import get_password_hash

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == settings.INITIAL_ADMIN_USERNAME).first()
        if not existing:
            if not settings.DEBUG and settings.INITIAL_ADMIN_PASSWORD == "admin123":
                raise RuntimeError("生产环境必须配置非默认 INITIAL_ADMIN_PASSWORD")
            admin_user = User(
                username=settings.INITIAL_ADMIN_USERNAME,
                email="admin@ai-control-tower.com",
                full_name="系统管理员",
                hashed_password=get_password_hash(settings.INITIAL_ADMIN_PASSWORD),
                role="管理员",
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            print(f"👤 初始管理员账户已创建: {settings.INITIAL_ADMIN_USERNAME}")
        else:
            print(f"👤 管理员账户已存在: {settings.INITIAL_ADMIN_USERNAME}")
    except Exception as e:
        print(f"⚠️ 创建管理员失败: {e}")
    finally:
        db.close()


def _start_workflow_automation_scheduler():
    """统一调度邮件、日报、AI流程推进和告警复核。"""
    global fallback_scheduler
    from app.db.session import SessionLocal
    from app.services.workflow_automation import recover_interrupted_runs, seed_automation_tasks
    from app.services.workflow_center import consolidate_email_workflow_items

    db = SessionLocal()
    try:
        seed_automation_tasks(db)
        recovered = recover_interrupted_runs(db)
        if recovered:
            print(f"♻️ 已释放 {recovered} 条因服务重启中断的自动任务")
        merged = consolidate_email_workflow_items(db)
        if merged["merged_items"]:
            print(f"🧹 已归并 {merged['merged_items']} 条重复邮件流程事项")
    finally:
        db.close()
    if scheduler is None:
        fallback_scheduler = IntervalFallbackScheduler(
            seconds=60,
            job=_run_workflow_automation_dispatcher,
            initial_delay=5,
        )
        fallback_scheduler.start()
        print("🤖 自动推进兜底任务已启用: 每分钟检查邮件、日报和告警任务")
        return
    scheduler.add_job(
        _run_workflow_automation_dispatcher,
        "interval",
        minutes=1,
        next_run_time=datetime.now() + timedelta(seconds=5),
        id="workflow_automation_dispatcher",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    if not scheduler.running:
        scheduler.start()
    print("🤖 自动推进任务已启用: 每分钟检查邮件、日报和告警任务")


def _run_workflow_automation_dispatcher():
    from app.services.workflow_automation import dispatch_due_automation_tasks

    try:
        dispatch_due_automation_tasks()
    except Exception as exc:
        print(f"⚠️ 自动推进任务调度失败: {exc}")


def _start_daily_report_scheduler():
    """启动项目活动日报定时同步任务"""
    global fallback_scheduler
    if not settings.DAILY_REPORT_SYNC_ENABLED:
        print("⏸️ 项目活动日报定时同步未启用")
        return
    if not settings.DAILY_REPORT_API_KEY:
        print("⚠️ 项目活动日报 API Key 未配置，跳过定时同步")
        return
    if scheduler is None or CronTrigger is None:
        if fallback_scheduler and fallback_scheduler.running:
            return
        fallback_scheduler = DailyFallbackScheduler(
            settings.DAILY_REPORT_SYNC_HOUR,
            settings.DAILY_REPORT_SYNC_MINUTE,
            _run_daily_report_sync_job,
        )
        fallback_scheduler.start()
        print(
            f"🗓️ 项目活动日报兜底定时同步已启用: "
            f"每天 {settings.DAILY_REPORT_SYNC_HOUR:02d}:{settings.DAILY_REPORT_SYNC_MINUTE:02d}"
        )
        return
    if scheduler.running:
        return

    scheduler.add_job(
        _run_daily_report_sync_job,
        CronTrigger(
            hour=settings.DAILY_REPORT_SYNC_HOUR,
            minute=settings.DAILY_REPORT_SYNC_MINUTE,
            timezone="Asia/Shanghai",
        ),
        id="daily_report_sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    print(
        f"🗓️ 项目活动日报定时同步已启用: "
        f"每天 {settings.DAILY_REPORT_SYNC_HOUR:02d}:{settings.DAILY_REPORT_SYNC_MINUTE:02d}"
    )


def _run_daily_report_sync_job():
    """定时同步项目活动日报"""
    from app.db.session import SessionLocal
    from app.services.daily_report_sync import DailyReportSyncService

    db = SessionLocal()
    try:
        service = DailyReportSyncService(db)
        run = service.sync_month(
            lookback_days=settings.DAILY_REPORT_SYNC_LOOKBACK_DAYS,
            trigger_type="scheduled",
            trigger_ingestion=True,
        )
        print(
            f"✅ 日报同步完成: {run.month}, 导入 {run.imported_activity_count} 条, "
            f"未匹配 {run.unmatched_count} 条"
        )
    except Exception as e:
        print(f"⚠️ 日报同步任务失败: {e}")
    finally:
        db.close()


def _start_warning_scheduler():
    """每天在日报同步后生成项目与渠道预警。"""
    if not settings.ENABLE_WARNING_NOTIFICATION:
        print("⏸️ 预警定时检查未启用")
        return
    if scheduler is None or CronTrigger is None:
        print("⚠️ APScheduler 不可用，预警仅支持手动检查")
        return
    scheduler.add_job(
        _run_warning_check_job,
        CronTrigger(
            hour=settings.WARNING_CHECK_HOUR,
            minute=settings.WARNING_CHECK_MINUTE,
            timezone="Asia/Shanghai",
        ),
        id="warning_check",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    if not scheduler.running:
        scheduler.start()
    print(
        f"⚠️ 预警定时检查已启用: 每天 "
        f"{settings.WARNING_CHECK_HOUR:02d}:{settings.WARNING_CHECK_MINUTE:02d}"
    )


def _run_warning_check_job():
    from app.db.session import SessionLocal
    from app.api.v1.warnings import run_warning_check

    db = SessionLocal()
    try:
        created = run_warning_check(db)
        print(f"✅ 预警检查完成: 新增 {created} 条")
    except Exception as exc:
        db.rollback()
        print(f"⚠️ 预警检查失败: {exc}")
    finally:
        db.close()


def _start_intelligence_snapshot_scheduler():
    """每天在日报同步和预警检查之后固化一份可追溯情报快照。"""
    if scheduler is None or CronTrigger is None:
        print("⚠️ APScheduler 不可用，项目情报快照仅支持手工生成")
        return
    scheduler.add_job(
        _run_intelligence_snapshot_job,
        CronTrigger(
            hour=settings.INTELLIGENCE_SNAPSHOT_HOUR,
            minute=settings.INTELLIGENCE_SNAPSHOT_MINUTE,
            timezone="Asia/Shanghai",
        ),
        id="project_intelligence_snapshot",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    if not scheduler.running:
        scheduler.start()
    print(
        f"📈 项目情报快照已启用: 每天 "
        f"{settings.INTELLIGENCE_SNAPSHOT_HOUR:02d}:{settings.INTELLIGENCE_SNAPSHOT_MINUTE:02d}"
    )


def _run_intelligence_snapshot_job():
    from app.db.session import SessionLocal
    from app.services.project_intelligence import build_daily_snapshots

    db = SessionLocal()
    try:
        result = build_daily_snapshots(db)
        print(f"✅ 项目情报快照完成: 新增 {result['created']}，刷新 {result['updated']}")
    except Exception as exc:
        db.rollback()
        print(f"⚠️ 项目情报快照失败: {exc}")
    finally:
        db.close()


def _start_dingtalk_mail_scheduler():
    """配置并启用后，定时从钉钉企业邮箱拉取最近邮件。"""
    if scheduler is None:
        print("⚠️ APScheduler 不可用，钉钉企业邮箱仅支持手动同步")
        return
    scheduler.add_job(
        _run_dingtalk_mail_sync_job,
        "interval",
        minutes=max(1, settings.DINGTALK_MAIL_SYNC_INTERVAL_MINUTES),
        id="dingtalk_mail_sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    if not scheduler.running:
        scheduler.start()
    print(f"📧 钉钉企业邮箱定时同步已启用: 每 {settings.DINGTALK_MAIL_SYNC_INTERVAL_MINUTES} 分钟")


def _run_dingtalk_mail_sync_job():
    from app.db.session import SessionLocal
    from app.services.dingtalk_mail import DingTalkMailService

    db = SessionLocal()
    try:
        service = DingTalkMailService()
        if not service.enabled or not service.configured:
            return
        result = service.sync(
            db,
            max_messages=settings.DINGTALK_MAIL_SYNC_LIMIT,
            unseen_only=False,
        )
        print(
            f"✅ 钉钉邮箱同步完成: 新增 {result['imported_count']} 封, "
            f"重复 {result['duplicate_count']} 封, 失败 {result['failed_count']} 封"
        )
    except Exception as exc:
        db.rollback()
        print(f"⚠️ 钉钉邮箱同步失败: {exc}")
    finally:
        db.close()


def _start_overseas_performance_scheduler():
    """定期检查是否需要生成月度或季度海外绩效汇报。"""
    if scheduler is None:
        print("⚠️ APScheduler 不可用，海外绩效汇报仅支持手动生成")
        return
    scheduler.add_job(
        _run_overseas_performance_job,
        "interval",
        minutes=15,
        id="overseas_performance_report",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    if not scheduler.running:
        scheduler.start()
    print("📋 海外绩效汇报定时检查已启用: 每 15 分钟")


def _run_overseas_performance_job():
    from app.db.session import SessionLocal
    from app.services.overseas_performance import run_due_scheduled_reports

    db = SessionLocal()
    try:
        created = run_due_scheduled_reports(db)
        db.commit()
        if created:
            print(f"✅ 海外绩效汇报定时生成完成: 新增 {created} 份")
    except Exception as exc:
        db.rollback()
        print(f"⚠️ 海外绩效汇报定时生成失败: {exc}")
    finally:
        db.close()


# ============ 关闭事件 ============
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
    if fallback_scheduler and fallback_scheduler.running:
        fallback_scheduler.shutdown(wait=False)
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
